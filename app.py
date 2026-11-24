"""
Dashboard interactivo – Terremotos significativos 1965–2016 (USGS)
Tarea 4 – Programación para el análisis de datos (UNAD, 203008069)
Autor: Eynar Daniel Franco Leal – Grupo 33

Extensión comunicativa del EDA de la Tarea 3: mismos datos, misma limpieza
y mismas conclusiones, presentados para una audiencia no técnica.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from scipy import stats

st.set_page_config(page_title="Sismos significativos 1965–2016", page_icon="🌎", layout="wide")
sns.set_theme(style="whitegrid")

def dec(x, n=2):
    """Formatea un número con coma decimal (estilo colombiano)."""
    return f"{x:.{n}f}".replace(".", ",")


ORDEN_PROF = ["Superficial (<=70)", "Intermedio (70-300)", "Profundo (>300)"]
COLORES_PROF = {"Superficial (<=70)": "#3b6ea5", "Intermedio (70-300)": "#e8b88a", "Profundo (>300)": "#7a7a7a"}


# ---------------------------------------------------------------------------
# 1. Carga y limpieza (las mismas decisiones de la Tarea 3, Parte 0)
# ---------------------------------------------------------------------------
@st.cache_data
def cargar_datos(ruta: str = "database.csv") -> pd.DataFrame:
    df = pd.read_csv(ruta)
    # Columnas con más del 80 % de vacíos
    df = df.drop(columns=df.columns[df.isnull().mean() > 0.8])
    # Solo terremotos naturales (se excluyen explosiones nucleares y otros eventos)
    df = df[df["Type"] == "Earthquake"].copy()
    # Fecha y hora: 3 registros vienen en formato ISO, el resto mm/dd/aaaa
    iso = df["Date"].str.contains("T")
    fecha = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
    fecha[iso] = pd.to_datetime(df.loc[iso, "Date"], utc=True).dt.tz_localize(None)
    fecha[~iso] = pd.to_datetime(df.loc[~iso, "Date"] + " " + df.loc[~iso, "Time"], format="%m/%d/%Y %H:%M:%S")
    df["Datetime"] = fecha
    df["Year"] = df["Datetime"].dt.year
    # Profundidades negativas (3 registros con ruido de medición)
    df = df[df["Depth"] >= 0].copy()
    # Categoría de profundidad (criterio sismológico usado en la Tarea 3)
    df["Categoria_Prof"] = pd.cut(df["Depth"], bins=[-0.01, 70, 300, 700], labels=ORDEN_PROF)
    return df


df = cargar_datos()

# ---------------------------------------------------------------------------
# 2. Encabezado
# ---------------------------------------------------------------------------
st.title("🌎 Terremotos significativos en el mundo (1965–2016)")
st.markdown(
    "Análisis de **23.229 terremotos de magnitud 5,5 o mayor** registrados por el Servicio Geológico "
    "de los Estados Unidos (USGS). Use los filtros de la izquierda: todas las cifras y gráficos se "
    "actualizan con su selección."
)

# ---------------------------------------------------------------------------
# 3. Sidebar – filtros
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Filtros")
    cats = st.multiselect(
        "Profundidad del sismo",
        options=ORDEN_PROF,
        default=ORDEN_PROF,
        help="Superficial: hasta 70 km · Intermedio: 70 a 300 km · Profundo: más de 300 km",
    )
    mag_min, mag_max = float(df["Magnitude"].min()), float(df["Magnitude"].max())
    rango_mag = st.slider("Magnitud", mag_min, mag_max, (mag_min, mag_max), step=0.1)
    anio_min, anio_max = int(df["Year"].min()), int(df["Year"].max())
    rango_anio = st.slider("Años", anio_min, anio_max, (anio_min, anio_max))
    st.caption("Fuente: USGS, publicado en Kaggle (usgs/earthquake-database).")

df_f = df[
    df["Categoria_Prof"].isin(cats)
    & df["Magnitude"].between(*rango_mag)
    & df["Year"].between(*rango_anio)
]

if df_f.empty:
    st.warning("No hay sismos con esos filtros. Amplíe el rango de magnitud o de años, o elija otra profundidad.")
    st.stop()

tab_exp, tab_vis, tab_est, tab_hal = st.tabs(
    ["📋 Exploración de datos", "📊 Visualizaciones", "🧪 Validación estadística", "💡 Hallazgos"]
)

# ---------------------------------------------------------------------------
# 4. Exploración de datos
# ---------------------------------------------------------------------------
with tab_exp:
    st.subheader("Cifras clave según los filtros")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Sismos registrados", f"{len(df_f):,}".replace(",", "."))
    c2.metric("Magnitud media", dec(df_f["Magnitude"].mean()))
    c3.metric("Desviación estándar de la magnitud", dec(df_f["Magnitude"].std()) if len(df_f) > 1 else "–")
    c4.metric("Profundidad media", f"{df_f['Depth'].mean():.0f} km")

    st.subheader("Tabla de sismos")
    cols = ["Datetime", "Latitude", "Longitude", "Depth", "Categoria_Prof", "Magnitude", "Magnitude Type", "Status"]
    st.dataframe(
        df_f[cols].sort_values("Datetime", ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "Datetime": st.column_config.DatetimeColumn("Fecha y hora (UTC)", format="YYYY-MM-DD HH:mm"),
            "Latitude": st.column_config.NumberColumn("Latitud", format="%.2f"),
            "Longitude": st.column_config.NumberColumn("Longitud", format="%.2f"),
            "Depth": st.column_config.NumberColumn("Profundidad (km)", format="%.1f"),
            "Categoria_Prof": "Profundidad",
            "Magnitude": st.column_config.NumberColumn("Magnitud", format="%.1f"),
            "Magnitude Type": "Método de cálculo",
            "Status": "Estado de revisión",
        },
    )

# ---------------------------------------------------------------------------
# 5. Visualizaciones (gráficos de la Tarea 3, Parte 3)
# ---------------------------------------------------------------------------
with tab_vis:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**¿Qué tan fuertes suelen ser los sismos?**")
        fig, ax = plt.subplots(figsize=(6, 4))
        sns.histplot(df_f["Magnitude"], bins=30, kde=True, color="#3b6ea5", ax=ax)
        ax.set_xlabel("Magnitud")
        ax.set_ylabel("Número de sismos")
        ax.set_title("Distribución de la magnitud")
        st.pyplot(fig)
        plt.close(fig)
        st.caption("La mayoría de los sismos está cerca de 5,5–6. Los muy fuertes (8 o más) son pocos.")

    with col_b:
        st.markdown("**¿La profundidad cambia la fuerza del sismo?**")
        presentes = [c for c in ORDEN_PROF if c in df_f["Categoria_Prof"].unique()]
        fig, ax = plt.subplots(figsize=(6, 4))
        # Se pasa la categoría como texto: con el tipo categórico, seaborn desfasa los colores
        sns.violinplot(data=df_f.assign(Categoria_Prof=df_f["Categoria_Prof"].astype(str)), x="Categoria_Prof", y="Magnitude", order=presentes, hue="Categoria_Prof",
                       hue_order=presentes, palette=COLORES_PROF, inner="quartile", cut=0, legend=False, ax=ax)
        ax.set_xlabel("Profundidad (km)")
        ax.set_ylabel("Magnitud")
        ax.set_title("Magnitud según la profundidad")
        st.pyplot(fig)
        plt.close(fig)
        st.caption("Las tres formas son casi iguales: superficiales y profundos tienen fuerzas parecidas.")

    st.markdown("**¿Dónde ocurren?**")
    fig, ax = plt.subplots(figsize=(12, 5.5))
    mapa = df_f.assign(Profundidad=df_f["Categoria_Prof"].astype(str), Magnitud=df_f["Magnitude"])
    sns.scatterplot(data=mapa, x="Longitude", y="Latitude", hue="Profundidad", hue_order=presentes,
                    palette=COLORES_PROF, size="Magnitud", sizes=(4, 110), alpha=0.5, ax=ax)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xlabel("Longitud (°)")
    ax.set_ylabel("Latitud (°)")
    ax.set_title("Ubicación de los sismos: color = profundidad, tamaño = magnitud")
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    st.pyplot(fig)
    plt.close(fig)
    st.caption("Los sismos se concentran en franjas alrededor del océano Pacífico, donde chocan las placas tectónicas.")

    st.markdown("**¿Hay más sismos con los años?**")
    por_anio = df_f.groupby("Year").size()
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(por_anio.index, por_anio.values, marker="o", ms=3, color="#3b6ea5", label="Sismos por año")
    if len(por_anio) > 1:
        m, b = np.polyfit(por_anio.index, por_anio.values, 1)
        ax.plot(por_anio.index, m * por_anio.index + b, "--", color="#e8b88a", label=f"Tendencia ({m:+.1f} sismos/año)")
    ax.set_xlabel("Año")
    ax.set_ylabel("Cantidad de sismos")
    ax.set_title("Sismos registrados por año")
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)
    st.caption("El aumento se explica sobre todo porque hoy hay más estaciones que detectan sismos, no porque la Tierra tiemble más.")

# ---------------------------------------------------------------------------
# 6. Validación estadística (prueba t de Welch de la Tarea 3, Parte 1)
# ---------------------------------------------------------------------------
with tab_est:
    st.subheader("¿Los sismos superficiales son más fuertes que los profundos?")
    st.markdown(
        "Para responderlo se comparó la magnitud promedio de los sismos **superficiales** (hasta 70 km) "
        "con la de los **no superficiales** (más de 70 km), usando una prueba estadística que indica si "
        "la diferencia es real o si puede deberse al azar."
    )
    sup = df_f.loc[df_f["Categoria_Prof"] == ORDEN_PROF[0], "Magnitude"]
    nosup = df_f.loc[df_f["Categoria_Prof"] != ORDEN_PROF[0], "Magnitude"]

    if len(sup) > 1 and len(nosup) > 1:
        t, p = stats.ttest_ind(sup, nosup, equal_var=False)
        c1, c2, c3 = st.columns(3)
        c1.metric("Magnitud media – superficiales", dec(sup.mean()), help=f"{len(sup):,} sismos")
        c2.metric("Magnitud media – no superficiales", dec(nosup.mean()), help=f"{len(nosup):,} sismos")
        c3.metric("Valor p", dec(p, 3))
        if p >= 0.05:
            st.success(
                f"**No hay una diferencia real.** Las magnitudes promedio son prácticamente iguales "
                f"({dec(sup.mean())} frente a {dec(nosup.mean())}). La pequeña diferencia es del tamaño que "
                "cabría esperar por simple azar, así que la profundidad no sirve para anticipar qué tan fuerte será un sismo."
            )
        else:
            st.info(
                f"**Con estos filtros sí aparece una diferencia** ({dec(sup.mean())} frente a {dec(nosup.mean())}). "
                "Revise si es grande en la práctica: con muchos datos, diferencias muy pequeñas pueden resultar "
                "estadísticamente detectables sin tener importancia real."
            )
        with st.expander("Detalle técnico (para analistas)"):
            st.markdown(
                f"- Prueba t de Welch para dos muestras independientes (varianzas distintas).\n"
                f"- H0: la magnitud media es igual en ambos grupos. Nivel de significancia α = 0,05.\n"
                f"- Estadístico t = {t:.3f}; valor p = {p:.3f}; n = {len(sup):,} y {len(nosup):,}.\n"
                f"- Resultado con todos los datos (Tarea 3): t = 0,364; p = 0,716 → no se rechaza H0."
            )
    else:
        st.warning("Para esta comparación, los filtros deben incluir sismos superficiales y al menos una categoría más profunda.")

# ---------------------------------------------------------------------------
# 7. Hallazgos – narrativa para audiencia no técnica
#    BORRADOR: Daniel debe ajustarlo con sus palabras (Ejercicio IA T4-C).
# ---------------------------------------------------------------------------
with tab_hal:
    st.subheader("¿Qué analicé?")
    st.markdown(
        "Revisé más de 23.000 terremotos fuertes (magnitud 5,5 o mayor) ocurridos en todo el mundo entre 1965 "
        "y 2016. De cada uno se conoce cuándo ocurrió, dónde, a qué profundidad bajo la superficie y qué tan "
        "fuerte fue. La pregunta era si la profundidad y la ubicación ayudan a saber qué tan fuerte será un sismo."
    )
    st.subheader("¿Qué encontré?")
    st.markdown(
        "- **La profundidad no indica la fuerza.** Un sismo cercano a la superficie no es más fuerte que uno profundo: "
        "en promedio, los dos tipos tienen casi la misma magnitud (5,88).\n"
        "- **La ubicación indica dónde, no qué tan fuerte.** Los sismos se concentran en franjas alrededor del "
        "océano Pacífico, en los bordes de las placas tectónicas, pero en esas zonas hay sismos de todas las fuerzas.\n"
        "- **Cada año se registran más sismos**, pero la fuerza promedio se mantiene cerca de 5,9.\n"
        "- **Los sismos muy fuertes son pocos pero reales:** 40 sismos de magnitud 8 o más, como Sumatra 2004 y Japón 2011."
    )
    c1, c2 = st.columns(2)
    with c1:
        conteo = df.groupby("Categoria_Prof", observed=True)["Magnitude"].agg(["mean", "size"]).reindex(ORDEN_PROF)
        fig, ax = plt.subplots(figsize=(5.5, 3.8))
        ax.bar(["Superficiales", "Intermedios", "Profundos"], conteo["mean"],
               color=[COLORES_PROF[c] for c in ORDEN_PROF])
        ax.set_ylim(5.5, 6.1)
        for i, v in enumerate(conteo["mean"]):
            ax.text(i, v + 0.01, f"{v:.2f}", ha="center")
        ax.set_ylabel("Fuerza promedio (magnitud)")
        ax.set_title("La fuerza promedio es casi igual\nsin importar la profundidad")
        st.pyplot(fig)
        plt.close(fig)
    with c2:
        decada = df.groupby((df["Year"] // 10) * 10).agg(sismos=("Magnitude", "size"))
        anios = df.groupby((df["Year"] // 10) * 10)["Year"].nunique()
        prom_anual = decada["sismos"] / anios
        fig, ax = plt.subplots(figsize=(5.5, 3.8))
        ax.bar([f"{int(d)}s" for d in prom_anual.index], prom_anual.values, color="#3b6ea5")
        ax.set_ylabel("Sismos registrados por año (promedio)")
        ax.set_title("Se registran más sismos porque\nhay más estaciones que los detectan")
        st.pyplot(fig)
        plt.close(fig)
    st.subheader("¿Qué significa?")
    st.markdown(
        "Para planear la prevención no basta con mirar qué tan profundo suele temblar en una zona: un sismo "
        "profundo puede ser tan fuerte como uno superficial. Lo que sí orienta es **dónde** tiembla con frecuencia. "
        "Además, el aumento de registros con los años refleja mejores equipos de medición, así que comparar "
        "décadas sin tenerlo en cuenta llevaría a pensar, por error, que hoy tiembla más."
    )
    st.subheader("¿Qué se recomendaría?")
    st.markdown(
        "1. Priorizar la gestión del riesgo y las normas de construcción en las zonas donde se concentran los sismos, "
        "sin descartar las zonas donde los sismos son profundos.\n"
        "2. Al comparar periodos, tener en cuenta que la capacidad de detección cambió con el tiempo.\n"
        "3. Para anticipar la fuerza de un sismo se necesitan otras variables (tipo de falla, suelo, cercanía a "
        "zonas pobladas); la profundidad por sí sola no basta."
    )
    st.caption("Este análisis muestra relaciones entre variables; no permite afirmar causas. Datos: USGS (1965–2016), sismos de magnitud ≥ 5,5.")

st.divider()
st.caption("Eynar Daniel Franco Leal · Programación para el análisis de datos (203008069) · UNAD · 2026")
