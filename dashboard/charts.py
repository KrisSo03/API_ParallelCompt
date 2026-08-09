"""Plotly chart builders used by the Streamlit application."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.config import CLUSTER_COLORS, CLUSTER_LABELS, METRICS


def profile_distribution(indicators: pd.DataFrame) -> go.Figure:
    data = (
        indicators.assign(
            Perfil=indicators["cluster_label"].map(CLUSTER_LABELS).fillna(
                indicators["cluster_label"]
            )
        )["Perfil"]
        .value_counts()
        .rename_axis("Perfil")
        .reset_index(name="Puntos")
    )
    translated_colors = {
        CLUSTER_LABELS.get(label, label): color for label, color in CLUSTER_COLORS.items()
    }
    figure = px.pie(
        data,
        names="Perfil",
        values="Puntos",
        hole=0.58,
        color="Perfil",
        color_discrete_map=translated_colors,
        height=350,
    )
    figure.update_traces(textposition="inside", textinfo="percent+label")
    figure.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def country_comparison_chart(comparison: pd.DataFrame) -> go.Figure:
    labels = {
        "solar_score": "Solar",
        "wind_score": "Eólico",
        "hybrid_score": "Híbrido",
    }
    long_data = comparison.melt(
        id_vars="country", var_name="Indicador", value_name="Potencial"
    )
    long_data["Indicador"] = long_data["Indicador"].map(labels)
    figure = px.bar(
        long_data,
        x="country",
        y="Potencial",
        color="Indicador",
        barmode="group",
        text="Potencial",
        color_discrete_map={
            "Solar": METRICS["solar_score"]["color"],
            "Eólico": METRICS["wind_score"]["color"],
            "Híbrido": METRICS["hybrid_score"]["color"],
        },
        height=430,
    )
    figure.update_traces(texttemplate="%{text:.0%}", textposition="outside")
    figure.update_layout(
        xaxis_title=None,
        yaxis_title="Potencial promedio",
        yaxis_tickformat=".0%",
        yaxis_range=[0, 1.12],
        legend_title_text="Indicador",
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def renewable_map(indicators: pd.DataFrame, metric: str | None = None) -> go.Figure:
    plot_data = indicators.copy()
    plot_data["Categoría"] = plot_data["cluster_label"].map(CLUSTER_LABELS).fillna(
        plot_data["cluster_label"]
    )
    profile_metrics = {
        "Solar-dominant": ("solar_score", "Potencial solar"),
        "Wind-dominant": ("wind_score", "Potencial eólico"),
        "Hybrid-high": ("hybrid_score", "Potencial híbrido"),
        "Lower-resource": ("hybrid_score", "Potencial combinado"),
    }
    if metric is None:
        plot_data["Métrica del perfil"] = plot_data["cluster_label"].map(
            lambda label: profile_metrics.get(label, ("hybrid_score", "Potencial"))[0]
        )
        plot_data["Nombre del potencial"] = plot_data["cluster_label"].map(
            lambda label: profile_metrics.get(label, ("hybrid_score", "Potencial"))[1]
        )
        plot_data["Valor del perfil"] = plot_data.apply(
            lambda row: row[row["Métrica del perfil"]], axis=1
        )
    else:
        plot_data["Nombre del potencial"] = METRICS[metric]["label"]
        plot_data["Valor del perfil"] = plot_data[metric]
    plot_data["Tamaño"] = plot_data["Valor del perfil"].fillna(0).clip(lower=0) + 0.08
    plot_data["Potencial visible"] = (
        plot_data["Valor del perfil"].fillna(0).clip(lower=0, upper=1).mul(100).round().astype(int).astype(str)
        + "%"
    )
    plot_data["Punto"] = plot_data["point_id"].astype(int)
    score_labels = {
        "solar_score": "Solar",
        "wind_score": "Eólico",
        "hybrid_score": "Híbrido",
    }
    plot_data["Fortaleza principal"] = plot_data.apply(
        lambda row: (
            lambda strongest: f"{score_labels[strongest]} ({float(row[strongest]):.0%})"
        )(max(score_labels, key=lambda score_column: float(row[score_column]))),
        axis=1,
    )
    plot_data["Detalle de potenciales"] = plot_data.apply(
        lambda row: "<br>".join(
            f"Índice {score_labels[column].lower()} relativo: {float(row[column]):.0%}"
            for column in sorted(
                score_labels,
                key=lambda score_column: float(row[score_column]),
                reverse=True,
            )
        ),
        axis=1,
    )

    translated_colors = {
        CLUSTER_LABELS.get(label, label): color for label, color in CLUSTER_COLORS.items()
    }
    center = {
        "lat": float(plot_data["latitude"].mean()),
        "lon": float(plot_data["longitude"].mean()),
    }
    figure = px.scatter_mapbox(
        plot_data,
        lat="latitude",
        lon="longitude",
        color="Categoría",
        size="Tamaño",
        text="Potencial visible",
        size_max=22,
        hover_name="country",
        custom_data=["Punto", "Categoría", "Fortaleza principal", "Detalle de potenciales"],
        color_discrete_map=translated_colors,
        center=center,
        zoom=4.15,
        height=590,
    )
    figure.update_traces(
        textposition="top center",
        textfont=dict(size=11, color="#12332D"),
        marker=dict(opacity=0.88),
        hovertemplate=(
            "<b>%{hovertext} · Punto %{customdata[0]}</b><br>"
            "Perfil regional: %{customdata[1]}<br>"
            "Fortaleza principal: %{customdata[2]}<br><br>"
            "%{customdata[3]}"
            "<extra></extra>"
        ),
    )
    figure.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0, r=0, t=10, b=0),
        legend_title_text="Perfil energético",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.01,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,.88)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def cluster_score_chart(indicators: pd.DataFrame, metric: str) -> go.Figure:
    grouped = (
        indicators.groupby(["cluster_id", "cluster_label"], as_index=False)[metric]
        .mean()
        .sort_values(metric, ascending=False)
    )
    grouped["Cluster"] = grouped.apply(
        lambda row: f"Cluster {int(row['cluster_id'])} · "
        f"{CLUSTER_LABELS.get(row['cluster_label'], row['cluster_label'])}",
        axis=1,
    )
    figure = px.bar(
        grouped,
        x=metric,
        y="Cluster",
        orientation="h",
        text=metric,
        color=metric,
        color_continuous_scale=[[0, "#DDE8E1"], [1, METRICS[metric]["color"]]],
        range_color=(0, 1),
        height=350,
    )
    figure.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    figure.update_layout(
        xaxis_title=METRICS[metric]["label"],
        yaxis_title=None,
        coloraxis_showscale=False,
        margin=dict(l=10, r=30, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def scalability_preview(summary: pd.DataFrame) -> go.Figure:
    successful = summary.copy()
    if "status" in successful:
        successful = successful[successful["status"] == "success"]
    successful["workers"] = pd.to_numeric(successful["workers"], errors="coerce")
    successful["elapsed_seconds"] = pd.to_numeric(
        successful["elapsed_seconds"], errors="coerce"
    )
    successful = successful.dropna(subset=["workers", "elapsed_seconds"])
    grouped = (
        successful.groupby("workers", as_index=False)["elapsed_seconds"]
        .median()
        .sort_values("workers")
    )
    grouped["Workers"] = grouped["workers"].astype(int).astype(str)
    figure = px.bar(
        grouped,
        x="elapsed_seconds",
        y="Workers",
        orientation="h",
        text="elapsed_seconds",
        color="elapsed_seconds",
        color_continuous_scale=[[0, "#72B38D"], [1, "#176D57"]],
        height=245,
    )
    figure.update_traces(texttemplate="%{text:.2f} s", textposition="outside")
    figure.update_layout(
        xaxis_title="Tiempo mediano (s)",
        yaxis_title=None,
        coloraxis_showscale=False,
        margin=dict(l=5, r=45, t=5, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def speedup_chart(performance: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=performance["workers"],
            y=performance["speedup"],
            mode="lines+markers+text",
            text=performance["speedup"],
            texttemplate="%{text:.2f}×",
            textposition="top center",
            name="Aceleración observada",
            line=dict(color="#176D57", width=4),
            marker=dict(size=10),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=performance["workers"],
            y=performance["workers"],
            mode="lines",
            name="Aceleración ideal",
            line=dict(color="#AAB7B1", width=2, dash="dash"),
        )
    )
    figure.update_layout(
        height=340,
        xaxis_title="Workers",
        yaxis_title="Cuántas veces más rápido",
        xaxis=dict(tickmode="array", tickvals=performance["workers"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(l=10, r=20, t=50, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def efficiency_chart(performance: pd.DataFrame) -> go.Figure:
    data = performance.copy()
    data["Eficiencia"] = data["eficiencia"] * 100
    figure = px.bar(
        data,
        x="workers",
        y="Eficiencia",
        text="Eficiencia",
        color="Eficiencia",
        color_continuous_scale=[[0, "#D9E3DF"], [1, "#176D57"]],
        range_color=(0, 100),
        height=320,
    )
    figure.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    figure.update_layout(
        xaxis_title="Workers",
        yaxis_title="Aprovechamiento de workers",
        yaxis_ticksuffix="%",
        yaxis_range=[0, 112],
        xaxis=dict(tickmode="array", tickvals=data["workers"]),
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=20, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def memory_chart(performance: pd.DataFrame) -> go.Figure:
    figure = px.bar(
        performance,
        x="workers",
        y="memoria_mediana_mb",
        text="memoria_mediana_mb",
        color="memoria_mediana_mb",
        color_continuous_scale=[[0, "#E8DFF2"], [1, "#7057A6"]],
        height=320,
    )
    figure.update_traces(texttemplate="%{text:.1f} MB", textposition="outside")
    maximum = float(performance["memoria_mediana_mb"].max())
    figure.update_layout(
        xaxis_title="Workers",
        yaxis_title="Memoria máxima mediana (MB)",
        yaxis_range=[0, maximum * 1.16],
        xaxis=dict(tickmode="array", tickvals=performance["workers"]),
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=20, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure
