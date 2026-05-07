from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st


def _prepare_chart_df(df: pd.DataFrame, x: str, y: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    if x not in df.columns or y not in df.columns:
        return pd.DataFrame()

    chart_df = df[[x, y]].copy()
    chart_df = chart_df.dropna(subset=[x, y])

    if chart_df.empty:
        return pd.DataFrame()

    chart_df[y] = pd.to_numeric(chart_df[y], errors="coerce")
    chart_df = chart_df.dropna(subset=[y])

    if chart_df.empty:
        return pd.DataFrame()

    chart_df[x] = chart_df[x].astype(str)
    return chart_df


def render_bar_chart(df: pd.DataFrame, x: str, y: str, title: str) -> None:
    chart_df = _prepare_chart_df(df, x, y)
    if chart_df.empty:
        st.info(f"No usable data available for {title}.")
        return

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(chart_df[x], chart_df[y])
    ax.set_title(title)
    ax.set_xlabel(x.replace("_", " ").title())
    ax.set_ylabel(y.replace("_", " ").title())
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_line_chart(df: pd.DataFrame, x: str, y: str, title: str) -> None:
    chart_df = _prepare_chart_df(df, x, y)
    if chart_df.empty:
        st.info(f"No usable data available for {title}.")
        return

    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(chart_df[x], chart_df[y], marker="o")
    ax.set_title(title)
    ax.set_xlabel(x.replace("_", " ").title())
    ax.set_ylabel(y.replace("_", " ").title())
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)