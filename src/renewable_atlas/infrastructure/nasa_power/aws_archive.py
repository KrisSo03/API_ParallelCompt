import json
import math
from datetime import UTC, datetime
from pathlib import Path

import dask.dataframe as dd
import fsspec
import pandas as pd
import pyarrow.parquet as pq
import xarray as xr

SOLAR_VARIABLES = (
    "ALLSKY_SFC_SW_DWN",
    "ALLSKY_SFC_SW_DNI",
    "ALLSKY_SFC_SW_DIFF",
    "CLRSKY_SFC_SW_DWN",
    "ALLSKY_KT",
    "CLOUD_AMT",
)

METEOROLOGICAL_VARIABLES = (
    "WS10M",
    "WS50M",
    "WD10M",
    "WD50M",
    "T2M",
    "T2MDEW",
    "PS",
    "RH2M",
    "QV2M",
    "PRECTOTCORR",
)

# T2M_MAX and T2M_MIN are derived from hourly T2M. Together these are the
# same 18 NASA POWER parameters used by the point API integration.
POWER_VARIABLES = (
    SOLAR_VARIABLES
    + METEOROLOGICAL_VARIABLES
    + (
        "T2M_MAX",
        "T2M_MIN",
    )
)

SOLAR_ZARR_URL = (
    "https://nasa-power.s3.amazonaws.com/syn1deg/temporal/power_syn1deg_hourly_temporal_lst.zarr"
)
METEOROLOGICAL_ZARR_URL = (
    "https://nasa-power.s3.amazonaws.com/merra2/temporal/power_merra2_hourly_temporal_lst.zarr"
)


class NasaPowerAwsStager:
    """Stream NASA POWER AWS Zarr data into bounded Parquet partitions."""

    def __init__(
        self,
        solar_url: str = SOLAR_ZARR_URL,
        meteorological_url: str = METEOROLOGICAL_ZARR_URL,
        dataset_opener=None,
    ):
        self.solar_url = solar_url
        self.meteorological_url = meteorological_url
        self._dataset_opener = dataset_opener or self._open_remote_dataset

    @staticmethod
    def _open_remote_dataset(url: str):
        mapper = fsspec.get_mapper(url)
        return xr.open_zarr(mapper, consolidated=True)

    def stage(
        self,
        points,
        output_dir: str | Path,
        start_date: str,
        end_date: str,
        target_gib: float = 5.0,
        size_basis: str = "logical",
    ) -> dict:
        if not points:
            raise ValueError("At least one grid point is required")
        if target_gib <= 0:
            raise ValueError("target_gib must be positive")
        if size_basis not in {"logical", "disk"}:
            raise ValueError("size_basis must be 'logical' or 'disk'")

        destination = Path(output_dir).resolve()
        partitions_dir = destination / "hourly"
        partitions_dir.mkdir(parents=True, exist_ok=True)
        if any(partitions_dir.glob("year=*/month=*/*.parquet")):
            raise FileExistsError(
                f"Staging directory is not empty: {partitions_dir}. Use a new experiment directory."
            )

        target_bytes = int(target_gib * 1024**3)
        solar = self._dataset_opener(self.solar_url)
        meteorological = self._dataset_opener(self.meteorological_url)
        months = pd.period_range(start=start_date, end=end_date, freq="M")

        logical_bytes = 0
        disk_bytes = 0
        row_count = 0
        partition_count = 0
        first_timestamp = None
        last_timestamp = None

        try:
            for month in months:
                month_start = max(pd.Timestamp(start_date), month.start_time)
                month_end = min(pd.Timestamp(end_date), month.end_time)
                frame = self._load_month(
                    solar,
                    meteorological,
                    points,
                    month_start,
                    month_end,
                )
                if frame.empty:
                    continue

                path = (
                    partitions_dir
                    / f"year={month.year:04d}"
                    / f"month={month.month:02d}"
                    / "part-000.parquet"
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                frame.to_parquet(path, index=False, compression="zstd")

                parquet_metadata = pq.ParquetFile(path).metadata
                logical_bytes += sum(
                    parquet_metadata.row_group(index).total_byte_size
                    for index in range(parquet_metadata.num_row_groups)
                )
                disk_bytes += path.stat().st_size
                row_count += len(frame)
                partition_count += 1
                first_timestamp = first_timestamp or frame["timestamp"].min().isoformat()
                last_timestamp = frame["timestamp"].max().isoformat()

                measured_bytes = logical_bytes if size_basis == "logical" else disk_bytes
                if measured_bytes >= target_bytes:
                    break
        finally:
            solar.close()
            meteorological.close()

        measured_bytes = logical_bytes if size_basis == "logical" else disk_bytes
        manifest = {
            "status": "success" if measured_bytes >= target_bytes else "partial",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "source": "NASA POWER AWS Open Data",
            "solar_zarr": self.solar_url,
            "meteorological_zarr": self.meteorological_url,
            "variables": list(POWER_VARIABLES),
            "variable_count": len(POWER_VARIABLES),
            "derived_variables": ["T2M_MAX", "T2M_MIN"],
            "point_count": len(points),
            "row_count": row_count,
            "partition_count": partition_count,
            "first_timestamp": first_timestamp,
            "last_timestamp": last_timestamp,
            "target_gib": target_gib,
            "size_basis": size_basis,
            "logical_uncompressed_gib": logical_bytes / 1024**3,
            "disk_gib": disk_bytes / 1024**3,
            "data_path": str(partitions_dir),
        }
        (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    @staticmethod
    def _load_month(solar, meteorological, points, start, end) -> pd.DataFrame:
        point_ids = xr.DataArray(range(len(points)), dims="point", name="point")
        latitudes = xr.DataArray(
            [point.latitude for point in points], dims="point", coords={"point": point_ids}
        )
        longitudes = xr.DataArray(
            [point.longitude for point in points], dims="point", coords={"point": point_ids}
        )

        solar_subset = solar[list(SOLAR_VARIABLES)].sel(time=slice(start, end)).sel(
            lat=latitudes, lon=longitudes, method="nearest"
        )
        meteorological_subset = meteorological[list(METEOROLOGICAL_VARIABLES)].sel(
            time=slice(start, end)
        ).sel(lat=latitudes, lon=longitudes, method="nearest")
        solar_frame = NasaPowerAwsStager._to_frame(solar_subset, SOLAR_VARIABLES)
        meteorological_frame = NasaPowerAwsStager._to_frame(
            meteorological_subset, METEOROLOGICAL_VARIABLES
        )
        frame = solar_frame.merge(
            meteorological_frame,
            on=["timestamp", "point_id"],
            how="inner",
            validate="one_to_one",
        )
        frame["date"] = frame["timestamp"].dt.floor("D")
        daily_temperature = frame.groupby(["point_id", "date"])["T2M"]
        frame["T2M_MAX"] = daily_temperature.transform("max")
        frame["T2M_MIN"] = daily_temperature.transform("min")
        frame["latitude"] = frame["point_id"].map(
            {index: point.latitude for index, point in enumerate(points)}
        )
        frame["longitude"] = frame["point_id"].map(
            {index: point.longitude for index, point in enumerate(points)}
        )
        frame["country"] = frame["point_id"].map(
            {index: point.country for index, point in enumerate(points)}
        )
        ordered_columns = [
            "timestamp",
            "date",
            "point_id",
            "latitude",
            "longitude",
            "country",
            *POWER_VARIABLES,
        ]
        return frame[ordered_columns].sort_values(["timestamp", "point_id"])

    @staticmethod
    def _to_frame(dataset, variables) -> pd.DataFrame:
        frame = dataset[list(variables)].load().to_dataframe().reset_index()
        frame = frame.rename(columns={"time": "timestamp", "point": "point_id"})
        return frame.drop(columns=["lat", "lon"], errors="ignore")


class NasaPowerAwsProcessor:
    """Aggregate staged hourly data without loading the full dataset into RAM."""

    COLUMN_MAP = {
        "ALLSKY_SFC_SW_DWN": "sw_dwn_mean",
        "ALLSKY_SFC_SW_DNI": "dni_mean",
        "WS50M": "ws_50m_mean",
        "WS10M": "ws_10m_mean",
        "ALLSKY_SFC_SW_DIFF": "sw_diff_mean",
        "CLRSKY_SFC_SW_DWN": "clr_sky_sw_dwn_mean",
        "ALLSKY_KT": "allsky_kt_mean",
        "WD10M": "wd_10m_mean",
        "WD50M": "wd_50m_mean",
        "T2M": "t2m_mean",
        "T2M_MAX": "t2m_max_mean",
        "T2M_MIN": "t2m_min_mean",
        "T2MDEW": "t2mdew_mean",
        "PS": "ps_mean",
        "RH2M": "rh2m_mean",
        "QV2M": "qv2m_mean",
        "PRECTOTCORR": "prectotcorr_mean",
        "CLOUD_AMT": "cloud_amt_mean",
    }

    def process(
        self,
        staging_dir: str | Path,
        workers: int = 1,
        scheduler: str = "threads",
    ) -> pd.DataFrame:
        from renewable_atlas.application.services.scoring_service import ScoringService

        if workers < 1:
            raise ValueError("workers must be at least 1")
        if scheduler not in {"threads", "processes"}:
            raise ValueError("scheduler must be 'threads' or 'processes'")

        source = str(Path(staging_dir).resolve() / "hourly" / "year=*" / "month=*" / "*.parquet")
        frame = dd.read_parquet(source, engine="pyarrow")
        required = {
            "point_id",
            "latitude",
            "longitude",
            "country",
            *self.COLUMN_MAP,
        }
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"AWS staging data is missing columns: {', '.join(missing)}")

        identities = frame[["point_id", "latitude", "longitude", "country"]].drop_duplicates()
        means = frame[["point_id", *self.COLUMN_MAP]].groupby("point_id").mean()
        indicators = identities.merge(means.reset_index(), on="point_id").compute(
            scheduler=scheduler,
            num_workers=workers,
        )
        indicators = indicators.rename(columns=self.COLUMN_MAP)

        # Convert mean hourly irradiance (W/m²) to mean daily energy (kWh/m²/day),
        # matching the daily NASA POWER point API used by the existing pipeline.
        for column in (
            "sw_dwn_mean",
            "dni_mean",
            "sw_diff_mean",
            "clr_sky_sw_dwn_mean",
        ):
            indicators[column] = indicators[column] * 24.0 / 1000.0
        indicators["prectotcorr_mean"] = indicators["prectotcorr_mean"] * 24.0
        indicators["ws_100m_mean"] = indicators["ws_50m_mean"] * math.pow(2.0, 0.143)
        indicators["solar_score"] = 0.0
        indicators["wind_score"] = 0.0
        indicators["hybrid_score"] = 0.0
        return ScoringService().score(indicators).sort_values("point_id").reset_index(drop=True)


class NasaPowerAwsSequentialProcessor(NasaPowerAwsProcessor):
    """Main-equivalent baseline: pandas only, one partition at a time."""

    def process(self, staging_dir: str | Path) -> pd.DataFrame:
        from renewable_atlas.application.services.scoring_service import ScoringService

        paths = sorted((Path(staging_dir).resolve() / "hourly").glob("year=*/month=*/*.parquet"))
        if not paths:
            raise FileNotFoundError(f"No AWS Parquet partitions found in {staging_dir}")

        required = {
            "point_id",
            "latitude",
            "longitude",
            "country",
            *self.COLUMN_MAP,
        }
        partials = []
        identities = []
        for path in paths:
            frame = pd.read_parquet(path, columns=sorted(required))
            missing = sorted(required - set(frame.columns))
            if missing:
                raise ValueError(f"AWS staging data is missing columns: {', '.join(missing)}")
            identities.append(
                frame[["point_id", "latitude", "longitude", "country"]].drop_duplicates()
            )
            grouped = frame.groupby("point_id")[list(self.COLUMN_MAP)].agg(["sum", "count"])
            grouped.columns = [f"{column}__{stat}" for column, stat in grouped.columns]
            partials.append(grouped)

        totals = pd.concat(partials).groupby(level=0).sum()
        means = pd.DataFrame(index=totals.index)
        for source_column in self.COLUMN_MAP:
            means[source_column] = (
                totals[f"{source_column}__sum"] / totals[f"{source_column}__count"]
            )
        identity_frame = pd.concat(identities).drop_duplicates(subset=["point_id"])
        indicators = identity_frame.merge(means.reset_index(), on="point_id")
        indicators = indicators.rename(columns=self.COLUMN_MAP)

        for column in (
            "sw_dwn_mean",
            "dni_mean",
            "sw_diff_mean",
            "clr_sky_sw_dwn_mean",
        ):
            indicators[column] = indicators[column] * 24.0 / 1000.0
        indicators["prectotcorr_mean"] = indicators["prectotcorr_mean"] * 24.0
        indicators["ws_100m_mean"] = indicators["ws_50m_mean"] * math.pow(2.0, 0.143)
        indicators["solar_score"] = 0.0
        indicators["wind_score"] = 0.0
        indicators["hybrid_score"] = 0.0
        return ScoringService().score(indicators).sort_values("point_id").reset_index(drop=True)
