"""Contextual help: a collapsible "How to read this" box at the top of every page and section, in English and Spanish."""
from __future__ import annotations

import streamlit as st

from i18n import es
from ui import esc

# Each entry: title, what (one paragraph), how (steps to read it), terms (term, meaning), keep (caveats).
HELP: dict[str, dict[str, dict]] = {
    # ------------------------------------------------------------------ Markets
    "markets": {
        "en": {
            "title": "Markets",
            "what": "A one-screen snapshot of the day: the main US indices, sectors, interest rates, Mexico and Argentina, your watchlist and an AI note that summarises the news.",
            "how": [
                "Start with the index cards: the big number is the price, the coloured pill is today's change and the bar shows where the price sits between today's low (left) and high (right).",
                "Sector bars tell you what is leading and lagging today. When defensive sectors (utilities, consumer staples, health care) lead, investors are usually cautious; when technology and consumer discretionary lead, they are taking risk.",
                "The yield curve shows what the US government pays to borrow for each term. Normally longer terms pay more (an upward curve). If short rates are above long rates (an inverted curve), markets expect rate cuts and slower growth.",
                "The morning note links each story to its sources: open them before relying on a summary.",
            ],
            "terms": [
                ("ETF", "A fund that trades like a stock. Indices can't be bought directly, so the app shows the ETF that tracks each one (SPY for the S&P 500, QQQ for the Nasdaq 100, and so on)."),
                ("Basis point (bps)", "One hundredth of a percentage point: 25 bps = 0.25%."),
                ("10Y − 2Y spread", "The 10-year yield minus the 2-year yield. Negative means an inverted curve."),
                ("MEP / blue dollar", "Argentina's market exchange rates. The gap versus the official rate measures pressure on the peso."),
            ],
            "keep": ["Prices are from the latest quote or close: outside market hours they don't move.", "The AI note only rewrites the headlines and numbers on the page; it can still get nuance wrong."],
        },
        "es": {
            "title": "Mercados",
            "what": "Una foto del día en una pantalla: los principales índices de EE.UU., sectores, tasas, México y Argentina, tu watchlist y una nota de IA que resume las noticias.",
            "how": [
                "Empezá por las tarjetas de índices: el número grande es el precio, la píldora de color es la variación de hoy y la barra muestra dónde está el precio entre el mínimo (izquierda) y el máximo (derecha) del día.",
                "Las barras por sector muestran qué lidera y qué se queda atrás hoy. Cuando lideran los sectores defensivos (servicios públicos, consumo básico, salud), los inversores suelen estar cautos; cuando lideran tecnología y consumo discrecional, están tomando riesgo.",
                "La curva de rendimientos muestra cuánto paga el gobierno de EE.UU. por endeudarse a cada plazo. Lo normal es que los plazos largos paguen más (curva ascendente). Si las tasas cortas superan a las largas (curva invertida), el mercado espera recortes de tasas y menos crecimiento.",
                "La nota de la mañana enlaza cada historia con sus fuentes: abrilas antes de basarte en un resumen.",
            ],
            "terms": [
                ("ETF", "Un fondo que cotiza como una acción. Los índices no se pueden comprar directamente, así que la app muestra el ETF que replica cada uno (SPY para el S&P 500, QQQ para el Nasdaq 100, etc.)."),
                ("Punto básico (bps)", "Una centésima de punto porcentual: 25 bps = 0.25%."),
                ("Diferencial 10A − 2A", "El rendimiento a 10 años menos el de 2 años. Negativo significa curva invertida."),
                ("Dólar MEP / blue", "Tipos de cambio de mercado en Argentina. La brecha contra el oficial mide la presión sobre el peso."),
            ],
            "keep": ["Los precios son de la última cotización o cierre: fuera del horario de mercado no se mueven.", "La nota de IA solo reescribe los titulares y números de la página; igual puede equivocarse en matices."],
        },
    },
    # ------------------------------------------------------------------ News
    "news": {
        "en": {
            "title": "News desk",
            "what": "Headlines from official publisher feeds grouped by region (USA, Mexico, Argentina, World) and by sector, next to exchange rates and interest rates, with an AI read of what they mean for markets.",
            "how": [
                "Read 'Today's read' first for the big picture, then open the region or sector you care about.",
                "Each region and sector has a tone: Positive, Mixed or Negative. It describes the direction the headlines point to, not a forecast.",
                "Use the FX and rates boards to check the story against the numbers: a 'hawkish Fed' story should show up as higher yields, a 'peso under pressure' story as a higher USD/MXN.",
                "Sector tags on each headline come from keywords, so one headline can appear in more than one sector.",
            ],
            "terms": [
                ("Hawkish / dovish", "A central bank leaning towards higher rates (hawkish) or lower rates (dovish)."),
                ("ECB reference rate", "The daily exchange rate published by the European Central Bank; it updates once a day."),
                ("Country risk (EMBI)", "The extra yield Argentina's dollar bonds pay over US Treasuries, in basis points. Lower means more confidence."),
                ("Gap (brecha)", "How much a market dollar (MEP, CCL, blue) is above Argentina's official rate."),
            ],
            "keep": ["Headlines are from the last 36 hours (72 on weekends and Mondays).", "If a source is down the page says so at the bottom."],
        },
        "es": {
            "title": "Mesa de noticias",
            "what": "Titulares de los feeds oficiales de cada medio agrupados por región (EE.UU., México, Argentina, Mundo) y por sector, junto a tipos de cambio y tasas de interés, con una lectura de la IA sobre qué significan para los mercados.",
            "how": [
                "Leé primero 'La lectura de hoy' para el panorama general y después abrí la región o el sector que te interese.",
                "Cada región y sector tiene un tono: Positivo, Mixto o Negativo. Describe hacia dónde apuntan los titulares, no es un pronóstico.",
                "Usá los tableros de tipo de cambio y tasas para contrastar la historia con los números: una noticia de una 'Fed más dura' debería verse en rendimientos más altos; una de 'peso presionado', en un USD/MXN más alto.",
                "Las etiquetas de sector salen de palabras clave, así que un titular puede aparecer en más de un sector.",
            ],
            "terms": [
                ("Hawkish / dovish", "Un banco central que se inclina a subir tasas (hawkish) o a bajarlas (dovish)."),
                ("Tipo de referencia del BCE", "El tipo de cambio diario que publica el Banco Central Europeo; se actualiza una vez por día."),
                ("Riesgo país (EMBI)", "El rendimiento extra que pagan los bonos en dólares de Argentina sobre los del Tesoro de EE.UU., en puntos básicos. Más bajo = más confianza."),
                ("Brecha", "Cuánto está un dólar de mercado (MEP, CCL, blue) por encima del oficial."),
            ],
            "keep": ["Los titulares son de las últimas 36 horas (72 los fines de semana y los lunes).", "Si una fuente no responde, la página lo avisa al pie."],
        },
    },
    # ------------------------------------------------------------------ Map
    "map": {
        "en": {
            "title": "Market map",
            "what": "The 25 largest US companies as boxes: the size of each box is its market value and the colour is today's move.",
            "how": ["Big boxes move the index the most: a red Apple or Microsoft weighs more than a red Netflix.",
                    "Look for colour patterns by sector: a whole sector in red usually means a sector or macro story, a single red box a company story.",
                    "The tables below rank today's gainers and decliners; click a ticker to open it."],
            "terms": [("Market cap", "Share price × number of shares: what the market says the whole company is worth.")],
            "keep": ["Colours saturate at ±3%, so a 3% and a 10% move look equally intense."],
        },
        "es": {
            "title": "Mapa del mercado",
            "what": "Las 25 empresas más grandes de EE.UU. como cajas: el tamaño es su valor de mercado y el color es el movimiento de hoy.",
            "how": ["Las cajas grandes son las que más mueven el índice: un Apple o Microsoft en rojo pesa más que un Netflix en rojo.",
                    "Buscá patrones de color por sector: un sector entero en rojo suele indicar una historia sectorial o macro; una sola caja roja, una historia de esa empresa.",
                    "Las tablas de abajo ordenan las mayores alzas y bajas del día; hacé clic en un ticker para abrirlo."],
            "terms": [("Capitalización", "Precio de la acción × cantidad de acciones: lo que el mercado dice que vale toda la empresa.")],
            "keep": ["Los colores se saturan en ±3%, así que un movimiento de 3% y uno de 10% se ven igual de intensos."],
        },
    },
    # ------------------------------------------------------------------ Watchlist
    "watchlist": {
        "en": {
            "title": "Watchlist",
            "what": "Up to eight stocks side by side, like a screener: price, returns, risk, valuation and the next earnings date.",
            "how": [
                "Compare returns across periods (1M, 3M, YTD, 1Y) to tell a short bounce from a long trend.",
                "Volatility and max drawdown tell you how bumpy the ride has been; beta tells you how much the stock tends to move with the market.",
                "The 52-week bar shows whether the stock trades near its yearly low (left) or high (right).",
                "DCF value and Upside come from a simple model with default assumptions: a starting point to open the Valuation tab, not a verdict.",
            ],
            "terms": [
                ("P/E", "Price ÷ earnings per share. How many years of current profit you pay for. Compare it with peers, not in isolation."),
                ("Volatility", "Annualised standard deviation of daily returns: the size of a typical yearly swing."),
                ("Beta", "Sensitivity to the S&P 500: 1.2 means the stock has tended to move 20% more than the market."),
                ("Max DD", "Maximum drawdown: the worst fall from a peak in the last year."),
                ("n/m", "Not meaningful, for example a P/E when the company loses money."),
            ],
            "keep": ["The list is saved in the page address: bookmark it to keep it."],
        },
        "es": {
            "title": "Watchlist",
            "what": "Hasta ocho acciones lado a lado, como un screener: precio, rendimientos, riesgo, valuación y la fecha del próximo reporte.",
            "how": [
                "Compará los rendimientos en distintos períodos (1M, 3M, en el año, 1A) para distinguir un rebote corto de una tendencia larga.",
                "La volatilidad y la caída máxima muestran cuán movido fue el camino; la beta, cuánto tiende a moverse la acción con el mercado.",
                "La barra de 52 semanas muestra si la acción cotiza cerca de su mínimo (izquierda) o de su máximo (derecha) del año.",
                "El valor DCF y el potencial salen de un modelo simple con supuestos por defecto: un punto de partida para abrir la pestaña Valuación, no un veredicto.",
            ],
            "terms": [
                ("P/U", "Precio ÷ utilidad por acción. Cuántos años de la utilidad actual estás pagando. Comparalo con sus pares, no solo."),
                ("Volatilidad", "Desvío estándar anualizado de los rendimientos diarios: el tamaño de una oscilación anual típica."),
                ("Beta", "Sensibilidad al S&P 500: 1.2 significa que la acción tendió a moverse 20% más que el mercado."),
                ("Caída máx.", "La peor caída desde un máximo en el último año."),
                ("n/m", "No significativo, por ejemplo un P/U cuando la empresa pierde dinero."),
            ],
            "keep": ["La lista se guarda en la dirección de la página: guardala en favoritos para conservarla."],
        },
    },
    # ------------------------------------------------------------------ Compare
    "compare": {
        "en": {
            "title": "Compare",
            "what": "Several stocks rebased to the same starting point so you can see who did better over a period, with risk statistics and correlations.",
            "how": [
                "All lines start at 0% on the first day of the period: the end label is each one's total return.",
                "Return alone is not enough: check volatility and max drawdown to see the risk taken to get it. Sharpe puts both together.",
                "The equal-weight portfolio shows what holding the chosen stocks in equal parts would have done; if its volatility is below the average of the single stocks, diversification is working.",
                "In the correlation grid, values near +1 mean two stocks move together (little diversification); near 0 or negative means they help each other.",
            ],
            "terms": [
                ("Annualised return", "The yearly rate that would give the same total return."),
                ("Sharpe", "Return above the 10-year Treasury divided by volatility: return per unit of risk."),
                ("Correlation", "From −1 to +1, how closely two daily return series move together."),
            ],
            "keep": ["Past returns don't predict future ones; the period you pick can change the story a lot."],
        },
        "es": {
            "title": "Comparar",
            "what": "Varias acciones llevadas al mismo punto de partida para ver cuál rindió más en un período, con estadísticas de riesgo y correlaciones.",
            "how": [
                "Todas las líneas arrancan en 0% el primer día del período: la etiqueta final es el rendimiento total de cada una.",
                "El rendimiento solo no alcanza: mirá la volatilidad y la caída máxima para ver el riesgo asumido. El Sharpe junta ambas cosas.",
                "El portafolio de pesos iguales muestra qué habría pasado teniendo las acciones elegidas en partes iguales; si su volatilidad es menor que el promedio de las acciones individuales, la diversificación está funcionando.",
                "En la grilla de correlación, valores cerca de +1 significan que dos acciones se mueven juntas (poca diversificación); cerca de 0 o negativos, que se ayudan entre sí.",
            ],
            "terms": [
                ("Rendimiento anualizado", "La tasa anual que daría el mismo rendimiento total."),
                ("Sharpe", "Rendimiento por encima del bono del Tesoro a 10 años dividido por la volatilidad: rendimiento por unidad de riesgo."),
                ("Correlación", "De −1 a +1, cuánto se mueven juntas dos series de rendimientos diarios."),
            ],
            "keep": ["Los rendimientos pasados no predicen los futuros; el período que elijas puede cambiar mucho la historia."],
        },
    },
    # ------------------------------------------------------------------ Research
    "research": {
        "en": {
            "title": "Research",
            "what": "Investment pitches with a live track record. Each pitch is a call (Long, Short or Neutral) made on a date; the app measures it against the S&P 500 from that day.",
            "how": [
                "Stock return is how much the stock moved since the pitch; 'Call vs S&P 500' is that return minus the index's, with the sign flipped for Short calls. Positive means the call beat the market.",
                "'Beat the S&P 500' counts how many calls did so; the averages summarise the whole track record.",
                "To publish a pitch: 'Write a pitch' builds a file with today's date and price; upload it to the research folder on GitHub and it appears here.",
                "A good pitch has a clear thesis, a valuation that supports a target, catalysts with timing, and the risks that would prove it wrong.",
            ],
            "terms": [
                ("Long / Short", "Long = you expect the stock to beat the market; Short = you expect it to lag."),
                ("Catalyst", "An event that could make the market agree with your view (earnings, a product, a regulatory decision)."),
                ("Price target", "Your estimate of what the stock is worth over the stated horizon."),
            ],
            "keep": ["Returns use prices only (no dividends).", "A short track record says little: judge it after several calls and months."],
        },
        "es": {
            "title": "Research",
            "what": "Tesis de inversión con historial en vivo. Cada tesis es una recomendación (Long, Short o Neutral) hecha en una fecha; la app la mide contra el S&P 500 desde ese día.",
            "how": [
                "El rendimiento de la acción es cuánto se movió desde la tesis; 'Recomendación vs S&P 500' es ese rendimiento menos el del índice, con el signo invertido para los Short. Positivo significa que la recomendación le ganó al mercado.",
                "'Le ganaron al S&P 500' cuenta cuántas lo lograron; los promedios resumen todo el historial.",
                "Para publicar: 'Escribir una tesis' arma un archivo con la fecha y el precio de hoy; subilo a la carpeta research en GitHub y aparece acá.",
                "Una buena tesis tiene una idea clara, una valuación que respalde el objetivo, catalizadores con fecha y los riesgos que la invalidarían.",
            ],
            "terms": [
                ("Long / Short", "Long = esperás que la acción le gane al mercado; Short = esperás que quede atrás."),
                ("Catalizador", "Un evento que puede hacer que el mercado coincida con tu visión (resultados, un producto, una decisión regulatoria)."),
                ("Precio objetivo", "Tu estimación de lo que vale la acción en el horizonte indicado."),
            ],
            "keep": ["Los rendimientos usan solo precios (sin dividendos).", "Un historial corto dice poco: evaluarlo después de varias recomendaciones y meses."],
        },
    },
    # ------------------------------------------------------------------ Stock sections
    "stock_summary": {
        "en": {
            "title": "Stock summary",
            "what": "The quote page: price chart, key statistics, performance against the S&P 500, analyst ratings, key price levels and the company profile.",
            "how": [
                "Use the range buttons (1D to 5Y) to switch the chart period; the extra lines are the 50- and 200-day averages.",
                "Price above its 200-day average is usually read as a long-term uptrend; below, a downtrend.",
                "'Performance vs S&P 500' shows whether the stock beat the market over each period ('Difference' column).",
                "Key levels show how far the price is from its 52-week high and low and from its moving averages.",
            ],
            "terms": [
                ("EPS (TTM)", "Earnings per share over the trailing twelve months."),
                ("Dividend yield", "Yearly dividends ÷ price."),
                ("Moving average", "The average closing price over the last N days; it smooths out daily noise."),
                ("Analyst consensus", "Average of brokerage ratings on a 1 (strong sell) to 5 (strong buy) scale."),
            ],
            "keep": ["Sell-side ratings lean positive in general: 'Buy' is far more common than 'Sell'."],
        },
        "es": {
            "title": "Resumen de la acción",
            "what": "La página de cotización: gráfico de precio, estadísticas clave, rendimiento contra el S&P 500, recomendaciones de analistas, niveles de precio clave y el perfil de la empresa.",
            "how": [
                "Usá los botones de rango (1D a 5A) para cambiar el período; las líneas son los promedios de 50 y 200 días.",
                "Un precio por encima de su promedio de 200 días suele leerse como tendencia alcista de largo plazo; por debajo, bajista.",
                "'Rendimiento vs S&P 500' muestra si la acción le ganó al mercado en cada período (columna 'Diferencia').",
                "Los niveles clave muestran qué tan lejos está el precio de su máximo y mínimo de 52 semanas y de sus promedios móviles.",
            ],
            "terms": [
                ("UPA (12M)", "Utilidad por acción de los últimos doce meses."),
                ("Rendimiento por dividendo", "Dividendos anuales ÷ precio."),
                ("Promedio móvil", "El precio de cierre promedio de los últimos N días; suaviza el ruido diario."),
                ("Consenso de analistas", "Promedio de las recomendaciones de los bancos en una escala de 1 (venta fuerte) a 5 (compra fuerte)."),
            ],
            "keep": ["Las recomendaciones de los bancos suelen ser optimistas: 'Compra' es mucho más común que 'Venta'."],
        },
    },
    "stock_chart": {
        "en": {
            "title": "Chart and indicators",
            "what": "A full-size price chart with technical indicators, the statistical range of typical moves and the drawdown history.",
            "how": [
                "Candles: each one is a day; green if it closed above its open, red if below; the thin lines are the day's high and low.",
                "Bollinger bands surround the 20-day average at ± two standard deviations: touching a band means an unusually large move, not automatically a reversal.",
                "RSI (0–100) measures the strength of recent gains vs losses: above 70 is often called overbought, below 30 oversold.",
                "The ±1σ range ahead shows where the price would land about 2 times in 3 if it keeps last year's volatility, with no direction assumed.",
            ],
            "terms": [
                ("σ (sigma)", "One standard deviation; about two thirds of outcomes fall within ±1σ."),
                ("Drawdown", "How far the price is below its previous peak at each moment."),
            ],
            "keep": ["Indicators describe the past; on their own they are weak signals."],
        },
        "es": {
            "title": "Gráfico e indicadores",
            "what": "Un gráfico de precio grande con indicadores técnicos, el rango estadístico de movimientos típicos y el historial de caídas.",
            "how": [
                "Velas: cada una es un día; verde si cerró arriba de la apertura, roja si cerró abajo; las líneas finas son el máximo y mínimo del día.",
                "Las bandas de Bollinger rodean el promedio de 20 días a ± dos desvíos estándar: tocar una banda indica un movimiento inusual, no necesariamente un giro.",
                "El RSI (0–100) mide la fuerza de las subas recientes frente a las bajas: arriba de 70 se suele llamar sobrecompra; debajo de 30, sobreventa.",
                "El rango ±1σ a futuro muestra dónde quedaría el precio unas 2 de cada 3 veces si mantiene la volatilidad del último año, sin suponer dirección.",
            ],
            "terms": [
                ("σ (sigma)", "Un desvío estándar; cerca de dos tercios de los resultados caen dentro de ±1σ."),
                ("Caída desde máximos", "Cuánto está el precio por debajo de su máximo previo en cada momento."),
            ],
            "keep": ["Los indicadores describen el pasado; solos son señales débiles."],
        },
    },
    "stock_financials": {
        "en": {
            "title": "Financials",
            "what": "Six years of annual results taken directly from the company's 10-K filings with the SEC: revenue, profits, cash flow and margins.",
            "how": [
                "Read top to bottom: revenue → gross profit (after direct costs) → operating income (after running the business) → net income (after interest and taxes).",
                "Free cash flow = operating cash flow − capital expenditures: the cash the business really generates, and what the DCF values.",
                "Margins show profitability per dollar of revenue; rising margins with rising revenue is the healthiest combination.",
            ],
            "terms": [
                ("Gross margin", "Gross profit ÷ revenue."),
                ("Operating margin", "Operating income ÷ revenue."),
                ("Capex", "Money spent on long-lived assets (plants, equipment, data centres)."),
                ("Net debt", "Debt minus cash and short-term investments."),
            ],
            "keep": ["Only US companies that file 10-Ks are covered; ETFs and foreign filers aren't.", "Companies label some items differently, so an occasional line may be missing."],
        },
        "es": {
            "title": "Finanzas",
            "what": "Seis años de resultados anuales tomados directamente de los reportes 10-K de la empresa ante la SEC: ingresos, utilidades, flujo de caja y márgenes.",
            "how": [
                "Leé de arriba hacia abajo: ingresos → utilidad bruta (después de costos directos) → utilidad operativa (después de operar el negocio) → utilidad neta (después de intereses e impuestos).",
                "Flujo de caja libre = flujo operativo − inversión de capital: el efectivo que el negocio genera de verdad, y lo que valúa el DCF.",
                "Los márgenes muestran la rentabilidad por cada dólar vendido; márgenes que suben junto con los ingresos es la combinación más sana.",
            ],
            "terms": [
                ("Margen bruto", "Utilidad bruta ÷ ingresos."),
                ("Margen operativo", "Utilidad operativa ÷ ingresos."),
                ("Capex", "Dinero invertido en activos de largo plazo (plantas, equipos, centros de datos)."),
                ("Deuda neta", "Deuda menos efectivo e inversiones de corto plazo."),
            ],
            "keep": ["Solo cubre empresas de EE.UU. que presentan 10-K; no ETFs ni emisores extranjeros.", "Las empresas etiquetan algunas partidas distinto, así que alguna línea puede faltar."],
        },
    },
    "stock_valuation": {
        "en": {
            "title": "Valuation",
            "what": "What the company could be worth: a discounted cash flow (DCF) model you can adjust, scenarios, a reverse DCF, multiples and a comparison with peers.",
            "how": [
                "The DCF projects free cash flow for 10 years and discounts it back at the WACC: the result is the intrinsic value per share, compared with the market price.",
                "Open 'DCF assumptions' to change growth, terminal growth and the discount rate; everything updates. Small changes in these inputs move the value a lot.",
                "The reverse DCF answers the opposite question: what growth is the market already pricing in? Compare it with the company's past growth.",
                "The football field puts all valuation ranges on one axis against today's price; the comparable companies table shows what the stock would be worth at its peers' multiples.",
            ],
            "terms": [
                ("WACC", "Weighted average cost of capital: the return investors require, used as the discount rate."),
                ("Terminal growth", "The growth rate assumed forever after year 10; it should stay near long-run inflation or GDP growth."),
                ("Bear / Bull", "Pessimistic and optimistic scenarios (growth ±5 points, discount rate ±1 point)."),
                ("EV/EBITDA", "Company value including debt ÷ operating profit before depreciation; compares firms with different debt levels."),
                ("Peer median", "The middle value of the peer group's multiples, less distorted by outliers than the average."),
            ],
            "keep": ["A DCF is only as good as its assumptions: treat it as a range, not a single number.", "Edit the peer group: Finnhub's suggestion is not always a good match."],
        },
        "es": {
            "title": "Valuación",
            "what": "Cuánto podría valer la empresa: un modelo de flujos descontados (DCF) que podés ajustar, escenarios, un DCF inverso, múltiplos y una comparación con sus pares.",
            "how": [
                "El DCF proyecta el flujo de caja libre a 10 años y lo descuenta al WACC: el resultado es el valor intrínseco por acción, que se compara con el precio de mercado.",
                "Abrí 'Supuestos del DCF' para cambiar el crecimiento, el crecimiento terminal y la tasa de descuento; todo se actualiza. Cambios chicos en estos supuestos mueven mucho el valor.",
                "El DCF inverso responde la pregunta opuesta: ¿qué crecimiento ya está descontando el mercado? Comparalo con el crecimiento pasado de la empresa.",
                "El football field pone todos los rangos de valuación en un mismo eje contra el precio de hoy; la tabla de comparables muestra cuánto valdría la acción con los múltiplos de sus pares.",
            ],
            "terms": [
                ("WACC", "Costo promedio ponderado del capital: el rendimiento que exigen los inversores, usado como tasa de descuento."),
                ("Crecimiento terminal", "La tasa de crecimiento que se supone para siempre después del año 10; debería estar cerca de la inflación o el crecimiento del PIB de largo plazo."),
                ("Pesimista / optimista", "Escenarios con crecimiento ±5 puntos y tasa de descuento ±1 punto."),
                ("EV/EBITDA", "Valor de la empresa incluyendo deuda ÷ utilidad operativa antes de depreciaciones; compara empresas con distinto nivel de deuda."),
                ("Mediana de pares", "El valor del medio de los múltiplos del grupo; se distorsiona menos que el promedio con valores extremos."),
            ],
            "keep": ["Un DCF vale lo que valen sus supuestos: tomalo como un rango, no como un número exacto.", "Editá el grupo de pares: la sugerencia de Finnhub no siempre es buena."],
        },
    },
    "stock_outlook": {
        "en": {
            "title": "Outlook (scenarios)",
            "what": "4,000 simulated six-month paths for the stock, built from its own real daily moves of the last two years, to see the range of plausible outcomes.",
            "how": [
                "The fan chart: the dark band holds the middle half of the scenarios, the light band 9 in 10; the dashed line is the median path.",
                "The scenario table gives the price at 1, 3 and 6 months for a bad (5th percentile), weak, middle, good and very good (95th percentile) case.",
                "The probability cards answer practical questions: how often did the simulated paths end higher, fall 20% at some point, or reach the 52-week high or the DCF value?",
                "Switch the trend assumption to see how much the result depends on assuming no trend, the market's average, or the stock's recent trend.",
            ],
            "terms": [
                ("Bootstrap", "Resampling real past daily moves at random to build new paths, which keeps crash days and rallies in their real proportions."),
                ("Percentile", "The 5th percentile is the value that 95% of the scenarios beat."),
            ],
            "keep": ["These are model probabilities, not forecasts: they assume the next six months look like a reshuffled version of the last two years."],
        },
        "es": {
            "title": "Escenarios",
            "what": "4,000 trayectorias simuladas a seis meses, armadas con los movimientos diarios reales de la acción en los últimos dos años, para ver el rango de resultados posibles.",
            "how": [
                "El gráfico de abanico: la banda oscura contiene la mitad central de los escenarios y la clara, 9 de cada 10; la línea punteada es la trayectoria mediana.",
                "La tabla de escenarios da el precio a 1, 3 y 6 meses para un caso malo (percentil 5), débil, medio, bueno y muy bueno (percentil 95).",
                "Las tarjetas de probabilidad responden preguntas prácticas: ¿cuántas trayectorias terminaron más arriba, cayeron 20% en algún momento o llegaron al máximo de 52 semanas o al valor DCF?",
                "Cambiá el supuesto de tendencia para ver cuánto depende el resultado de suponer sin tendencia, el promedio del mercado o la tendencia reciente de la acción.",
            ],
            "terms": [
                ("Bootstrap", "Volver a sortear movimientos diarios reales del pasado para armar trayectorias nuevas; mantiene los desplomes y rallies en su proporción real."),
                ("Percentil", "El percentil 5 es el valor que superan el 95% de los escenarios."),
            ],
            "keep": ["Son probabilidades del modelo, no pronósticos: suponen que los próximos seis meses se parecen a una versión mezclada de los últimos dos años."],
        },
    },
    "stock_compare": {
        "en": {
            "title": "Compare this stock",
            "what": "The stock against the S&P 500 and the companies you pick, all starting at 0% on the same day.",
            "how": ["The end labels show each one's return over the period; the table adds volatility, worst fall and correlation with this stock.",
                    "A peer that moves with low correlation can be a diversifier; a high one means similar risks."],
            "terms": [("Correlation", "From −1 to +1, how closely daily returns move together.")],
            "keep": ["For more options, including an equal-weight portfolio, use the Compare page."],
        },
        "es": {
            "title": "Comparar esta acción",
            "what": "La acción contra el S&P 500 y las empresas que elijas, todas arrancando en 0% el mismo día.",
            "how": ["Las etiquetas finales muestran el rendimiento de cada una en el período; la tabla suma volatilidad, peor caída y correlación con esta acción.",
                    "Un par con baja correlación puede diversificar; una alta indica riesgos parecidos."],
            "terms": [("Correlación", "De −1 a +1, cuánto se mueven juntos los rendimientos diarios.")],
            "keep": ["Para más opciones, incluido un portafolio de pesos iguales, usá la página Comparar."],
        },
    },
    "stock_news": {
        "en": {
            "title": "Company news",
            "what": "News about this company from the last 7 days, from Finnhub.",
            "how": ["Scan the titles for earnings, guidance, products, legal or management changes: those tend to move the stock.",
                    "Open the source before drawing conclusions; summaries can miss the point."],
            "terms": [("Guidance", "The company's own forecast for its coming results.")],
            "keep": ["The AI analysis in the last section reads these same headlines."],
        },
        "es": {
            "title": "Noticias de la empresa",
            "what": "Noticias de esta empresa de los últimos 7 días, de Finnhub.",
            "how": ["Buscá en los títulos resultados, guías, productos, temas legales o cambios de dirección: son lo que más suele mover la acción.",
                    "Abrí la fuente antes de sacar conclusiones; los resúmenes pueden no captar lo importante."],
            "terms": [("Guía (guidance)", "El pronóstico propio de la empresa para sus próximos resultados.")],
            "keep": ["El análisis de IA de la última sección lee estos mismos titulares."],
        },
    },
    "stock_analysts": {
        "en": {
            "title": "Analysts and AI take",
            "what": "Two opinions side by side: the Wall Street consensus (brokerage analysts) and an AI view built only from the data in the app, each with a Buy / Hold / Sell lean.",
            "how": [
                "The consensus score goes from 1 (strong sell) to 5 (strong buy); the bar shows how many analysts are in each camp and whether opinion improved or worsened over three months.",
                "The AI take explains its reasons and whether it agrees with Wall Street. It uses the DCF assumptions set in the Valuation tab, so changing them can change the lean.",
                "When the two disagree, read why: it is usually valuation (the AI leans on the DCF) versus business momentum (analysts).",
            ],
            "terms": [
                ("Conviction", "How strongly the AI holds its lean given the data: Low, Medium or High."),
                ("Sell-side", "Analysts at banks and brokers who publish ratings for clients."),
            ],
            "keep": ["Both are opinions, not advice. Price targets are not available on the free data plan."],
        },
        "es": {
            "title": "Analistas y opinión de la IA",
            "what": "Dos opiniones lado a lado: el consenso de Wall Street (analistas de bancos y brokers) y una visión de la IA construida solo con los datos de la app, cada una con una postura de Compra / Mantener / Venta.",
            "how": [
                "El puntaje de consenso va de 1 (venta fuerte) a 5 (compra fuerte); la barra muestra cuántos analistas hay en cada grupo y si la opinión mejoró o empeoró en tres meses.",
                "La opinión de la IA explica sus motivos y si coincide con Wall Street. Usa los supuestos del DCF de la pestaña Valuación, así que cambiarlos puede cambiar la postura.",
                "Cuando no coinciden, leé por qué: suele ser valuación (la IA se apoya en el DCF) contra el momento del negocio (los analistas).",
            ],
            "terms": [
                ("Convicción", "Qué tan firme es la postura de la IA según los datos: Baja, Media o Alta."),
                ("Sell-side", "Analistas de bancos y brokers que publican recomendaciones para sus clientes."),
            ],
            "keep": ["Ambas son opiniones, no asesoría. Los precios objetivo no están en el plan gratuito de datos."],
        },
    },
    # ------------------------------------------------------------------ Portfolio sections
    "pf_overview": {
        "en": {
            "title": "Portfolio overview",
            "what": "Your positions valued at today's prices: what you have, how much you made or lost, how it is spread and how it has evolved.",
            "how": [
                "Unrealized P&L is the gain or loss on positions you still hold; realized P&L is what you locked in when selling.",
                "The time-weighted return removes the effect of money you put in or took out, so it measures your investment decisions and can be compared with the S&P 500 over the same period.",
                "The donuts show concentration by position and by sector. 'Effective number of positions' turns that into one number: 10 equal positions give 10, one dominant position pulls it towards 1.",
            ],
            "terms": [
                ("Average cost", "What you paid per share on average, including fees."),
                ("Weight", "The position's share of the total value, cash included."),
            ],
            "keep": ["Values use the latest quote; positions without a quote are left out until it returns."],
        },
        "es": {
            "title": "Resumen del portafolio",
            "what": "Tus posiciones valuadas a precios de hoy: qué tenés, cuánto ganaste o perdiste, cómo está repartido y cómo evolucionó.",
            "how": [
                "La ganancia/pérdida no realizada es la de las posiciones que todavía tenés; la realizada es la que concretaste al vender.",
                "El rendimiento ponderado por tiempo elimina el efecto del dinero que pusiste o sacaste, así mide tus decisiones de inversión y se puede comparar con el S&P 500 en el mismo período.",
                "Las donas muestran la concentración por posición y por sector. El 'número efectivo de posiciones' lo resume en un número: 10 posiciones iguales dan 10; una posición dominante lo acerca a 1.",
            ],
            "terms": [
                ("Costo promedio", "Lo que pagaste por título en promedio, incluidas comisiones."),
                ("Peso", "La parte del valor total que representa la posición, efectivo incluido."),
            ],
            "keep": ["Los valores usan la última cotización; las posiciones sin cotización quedan fuera hasta que vuelva."],
        },
    },
    "pf_transactions": {
        "en": {
            "title": "Transactions and backup",
            "what": "Where you record what you did: buys, sells, dividends, deposits and withdrawals. Everything else in the portfolio is calculated from this list.",
            "how": [
                "Record each trade with its date, shares and price. If you don't record deposits, purchases larger than your cash are counted as new money.",
                "Use 'Cash balance' to set the cash you really have; the difference is stored as an adjustment.",
                "Download a backup regularly: the data lives only in this browser. Restore it here on another device or after clearing the browser.",
            ],
            "terms": [("Cash adjustment", "A correction so the app's cash matches your broker's.")],
            "keep": ["Only US-listed stocks and ETFs (including ADRs) can be recorded."],
        },
        "es": {
            "title": "Operaciones y respaldo",
            "what": "Donde registrás lo que hiciste: compras, ventas, dividendos, depósitos y retiros. Todo lo demás del portafolio se calcula a partir de esta lista.",
            "how": [
                "Registrá cada operación con su fecha, cantidad y precio. Si no registrás depósitos, las compras mayores a tu efectivo cuentan como dinero nuevo.",
                "Usá 'Saldo de efectivo' para fijar el efectivo que realmente tenés; la diferencia se guarda como un ajuste.",
                "Descargá un respaldo cada tanto: los datos viven solo en este navegador. Restauralo acá en otro dispositivo o después de borrar el navegador.",
            ],
            "terms": [("Ajuste de efectivo", "Una corrección para que el efectivo de la app coincida con el de tu broker.")],
            "keep": ["Solo se pueden registrar acciones y ETFs listados en EE.UU. (incluidos ADRs)."],
        },
    },
    "pf_risk": {
        "en": {
            "title": "Portfolio risk",
            "what": "How risky your current mix is, measured on the last two years of real daily prices, and which positions drive that risk.",
            "how": [
                "Volatility is the size of a typical yearly swing; max drawdown is the worst fall your current mix would have suffered; beta is how much it moves with the market.",
                "VaR answers 'how much could I lose on a bad day?': on 19 days out of 20 the loss was smaller than this. CVaR is the average loss on those worst days.",
                "In 'What drives the risk', a position whose share of risk is much larger than its share of value is the one making the portfolio bumpy.",
                "In the correlation grid, look for pairs above 0.75: they move together and diversify each other little.",
            ],
            "terms": [
                ("VaR 95%", "Value at Risk: the loss exceeded only 5% of the time."),
                ("CVaR", "Conditional VaR: the average loss when the VaR is exceeded."),
                ("Risk contribution", "Each position's share of the portfolio's total variance; it adds up to 100%."),
            ],
            "keep": ["It uses today's weights on past prices: a description of past behaviour, not a forecast."],
        },
        "es": {
            "title": "Riesgo del portafolio",
            "what": "Qué tan riesgosa es tu mezcla actual, medida con los últimos dos años de precios diarios reales, y qué posiciones generan ese riesgo.",
            "how": [
                "La volatilidad es el tamaño de una oscilación anual típica; la caída máxima es la peor caída que habría sufrido tu mezcla actual; la beta, cuánto se mueve con el mercado.",
                "El VaR responde '¿cuánto podría perder en un mal día?': en 19 de cada 20 días la pérdida fue menor. El CVaR es la pérdida promedio en esos peores días.",
                "En 'Qué genera el riesgo', una posición cuyo peso en el riesgo es mucho mayor que su peso en el valor es la que hace más volátil el portafolio.",
                "En la grilla de correlación buscá pares por encima de 0.75: se mueven juntos y se diversifican poco.",
            ],
            "terms": [
                ("VaR 95%", "Valor en riesgo: la pérdida que solo se supera el 5% de las veces."),
                ("CVaR", "VaR condicional: la pérdida promedio cuando se supera el VaR."),
                ("Contribución al riesgo", "La parte de la varianza total del portafolio que aporta cada posición; suma 100%."),
            ],
            "keep": ["Usa los pesos de hoy sobre precios pasados: describe el comportamiento pasado, no es un pronóstico."],
        },
    },
    "pf_profile": {
        "en": {
            "title": "Investor profile",
            "what": "Six questions that set how much risk fits you, and a check of your real portfolio against it.",
            "how": [
                "Answer for this money specifically. Three questions measure willingness (what you want), three measure capacity (what you can afford to lose); when they disagree, the lower one sets the profile, as advisers do.",
                "Each profile comes with guide rails: maximum volatility, the drawdown you said you could take, a limit per company and a minimum in cash and bonds.",
                "Below, each check is marked In line, Watch or Mismatch, with the reason.",
            ],
            "terms": [
                ("Willingness", "How much risk you want to take."),
                ("Capacity", "How much loss you can absorb given your horizon and liquidity needs."),
            ],
            "keep": ["The profile feeds the optimiser and the recommendations; update it when your situation changes."],
        },
        "es": {
            "title": "Perfil de inversionista",
            "what": "Seis preguntas que definen cuánto riesgo te corresponde, y una verificación de tu portafolio real contra eso.",
            "how": [
                "Respondé pensando en este dinero en particular. Tres preguntas miden la disposición (lo que querés) y tres la capacidad (lo que podés permitirte perder); si no coinciden, manda la más baja, como hacen los asesores.",
                "Cada perfil trae límites guía: volatilidad máxima, la caída que dijiste poder tolerar, un límite por empresa y un mínimo en efectivo y bonos.",
                "Abajo, cada verificación aparece como En línea, Atención o Desajuste, con el motivo.",
            ],
            "terms": [
                ("Disposición", "Cuánto riesgo querés asumir."),
                ("Capacidad", "Cuánta pérdida podés absorber según tu horizonte y tus necesidades de liquidez."),
            ],
            "keep": ["El perfil alimenta al optimizador y a las recomendaciones; actualizalo cuando cambie tu situación."],
        },
    },
    "pf_news": {
        "en": {
            "title": "News impact",
            "what": "Connects today's headlines (company news, the news desk and macro) with your positions and explains which way they could push each one and why.",
            "how": [
                "Each position gets a direction: Positive, Negative, Mixed or Uncertain, with the reasoning and the headlines behind it.",
                "'Review this position' appears only when the news looks material enough to check now; 'What to check' says what to look at.",
                "Macro factors (rates, the dollar, oil, regulation) list which of your positions they touch.",
            ],
            "terms": [("Macro factor", "A force that affects many companies at once, such as interest rates or the exchange rate.")],
            "keep": ["No numbers are given for the impact, and a negative headline is not a reason to sell by itself."],
        },
        "es": {
            "title": "Impacto de noticias",
            "what": "Conecta los titulares de hoy (noticias de cada empresa, la mesa de noticias y la macro) con tus posiciones y explica hacia dónde podrían empujar a cada una y por qué.",
            "how": [
                "Cada posición recibe una dirección: Positivo, Negativo, Mixto o Incierto, con el razonamiento y los titulares que la respaldan.",
                "'Revisar esta posición' aparece solo cuando la noticia parece lo bastante importante como para mirarla ahora; 'Qué revisar' dice qué mirar.",
                "Los factores macro (tasas, dólar, petróleo, regulación) indican a cuáles de tus posiciones afectan.",
            ],
            "terms": [("Factor macro", "Una fuerza que afecta a muchas empresas a la vez, como las tasas de interés o el tipo de cambio.")],
            "keep": ["No se dan cifras de impacto, y un titular negativo no es por sí solo un motivo para vender."],
        },
    },
    "pf_optimization": {
        "en": {
            "title": "Optimization (efficient frontier)",
            "what": "Shows the best possible mixes of your assets (plus optional diversifiers) for each level of risk, where your portfolio sits today, and how to move towards the mix that fits your profile.",
            "how": [
                "The blue curve is the efficient frontier: for each level of risk (horizontal axis) it gives the highest expected return (vertical axis). Portfolios below it take risk without being paid for it.",
                "The green zone is the risk your profile is comfortable with. 'Best for your profile' is the point with the most expected return inside that zone.",
                "Pick a portfolio with the buttons, or 'Choose my own risk level' to slide along the curve. The card on the right compares it with yours: green means better for you.",
                "'How the mix changes' and 'Moves to get there' translate the selected portfolio into what to buy and sell, in % and dollars.",
            ],
            "terms": [
                ("Minimum variance", "The calmest mix possible with these assets."),
                ("Maximum Sharpe", "The mix with the most expected return per unit of risk; the most efficient on paper, but sensitive to return estimates."),
                ("Expected return (CAPM)", "The return implied by each asset's market risk: 10-year Treasury + beta × 5%."),
                ("pp", "Percentage points: from 7% to 9% is +2 pp."),
            ],
            "keep": ["Optimisers amplify estimation errors: use the weights as a direction, not an exact recipe.", "Optimal mixes are fully invested; keep aside the cash you know you will need."],
        },
        "es": {
            "title": "Optimización (frontera eficiente)",
            "what": "Muestra las mejores mezclas posibles de tus activos (más diversificadores opcionales) para cada nivel de riesgo, dónde está tu portafolio hoy y cómo acercarte a la mezcla que corresponde a tu perfil.",
            "how": [
                "La curva azul es la frontera eficiente: para cada nivel de riesgo (eje horizontal) da el mayor rendimiento esperado (eje vertical). Los portafolios por debajo asumen riesgo sin que se les pague por él.",
                "La zona verde es el riesgo con el que tu perfil está cómodo. 'El mejor para tu perfil' es el punto con más rendimiento esperado dentro de esa zona.",
                "Elegí un portafolio con los botones, o 'Elegir mi nivel de riesgo' para recorrer la curva. La tarjeta de la derecha lo compara con el tuyo: verde significa mejor para vos.",
                "'Cómo cambia la mezcla' y 'Movimientos para llegar' traducen el portafolio elegido en qué comprar y vender, en % y en dólares.",
            ],
            "terms": [
                ("Mínima varianza", "La mezcla más tranquila posible con estos activos."),
                ("Máximo Sharpe", "La mezcla con más rendimiento esperado por unidad de riesgo; la más eficiente en teoría, pero sensible a las estimaciones de rendimiento."),
                ("Rendimiento esperado (CAPM)", "El rendimiento implícito por el riesgo de mercado de cada activo: bono a 10 años + beta × 5%."),
                ("pp", "Puntos porcentuales: de 7% a 9% son +2 pp."),
            ],
            "keep": ["Los optimizadores amplifican los errores de estimación: usá los pesos como una dirección, no como una receta exacta.", "Las mezclas óptimas están totalmente invertidas; reservá aparte el efectivo que sabés que vas a necesitar."],
        },
    },
    "pf_recommendations": {
        "en": {
            "title": "Recommendations",
            "what": "A signal for each position (Buy more, Hold, Reduce, Sell) and new ideas, computed from your profile, the optimiser, risk, valuation, analysts and the news read; the AI then explains them.",
            "how": [
                "The signals table shows the data behind each signal: current weight vs profile target, share of risk, 1-year return, DCF upside, analyst consensus and news.",
                "'Volatility after' is the whole portfolio's expected volatility if only that position moved to its target (cash absorbs the difference).",
                "New ideas are assets you don't own that the profile-optimal portfolio uses; the table shows how adding them would change risk and return.",
                "'Write the recommendations' asks the AI to explain each item: what, why, data, risk change and downsides. 'Keep as is' is a valid answer.",
            ],
            "terms": [
                ("Profile target", "The weight the profile-optimal portfolio gives that asset."),
                ("Turnover", "The share of the portfolio that would have to trade to rebalance."),
            ],
            "keep": ["The app never trades; taxes and fees are not included. Not investment advice."],
        },
        "es": {
            "title": "Recomendaciones",
            "what": "Una señal por posición (Comprar más, Mantener, Reducir, Vender) e ideas nuevas, calculadas a partir de tu perfil, el optimizador, el riesgo, la valuación, los analistas y la lectura de noticias; después la IA las explica.",
            "how": [
                "La tabla de señales muestra los datos detrás de cada una: peso actual vs objetivo del perfil, peso en el riesgo, rendimiento a 1 año, potencial DCF, consenso de analistas y noticias.",
                "'Volatilidad después' es la volatilidad esperada de todo el portafolio si solo esa posición fuera a su objetivo (el efectivo absorbe la diferencia).",
                "Las ideas nuevas son activos que no tenés y que usa el portafolio óptimo de tu perfil; la tabla muestra cómo cambiarían el riesgo y el rendimiento al agregarlos.",
                "'Escribir las recomendaciones' le pide a la IA que explique cada punto: qué, por qué, datos, cambio en el riesgo y desventajas. 'Mantener como está' es una respuesta válida.",
            ],
            "terms": [
                ("Objetivo del perfil", "El peso que le da a ese activo el portafolio óptimo de tu perfil."),
                ("Rotación (turnover)", "La parte del portafolio que habría que operar para rebalancear."),
            ],
            "keep": ["La app nunca opera; no incluye impuestos ni comisiones. No es asesoría de inversión."],
        },
    },
    "pf_simulator": {
        "en": {
            "title": "Simulator",
            "what": "Try changes before making them: edit the target shares of each position (or add new tickers) and compare risk and return before and after.",
            "how": [
                "Edit 'Target shares' or add a row with a new ticker, then press 'Compare before and after'.",
                "'Fill in the profile-optimal weights' loads the optimiser's suggestion as a starting point.",
                "If the changes cost more than your cash, the app tells you how much new money they would need.",
            ],
            "terms": [("Effective number of positions", "1 ÷ the sum of squared weights: how diversified the portfolio really is.")],
            "keep": ["Your saved portfolio is never changed here."],
        },
        "es": {
            "title": "Simulador",
            "what": "Probá cambios antes de hacerlos: editá los títulos objetivo de cada posición (o agregá tickers nuevos) y compará riesgo y rendimiento antes y después.",
            "how": [
                "Editá 'Títulos objetivo' o agregá una fila con un ticker nuevo y tocá 'Comparar antes y después'.",
                "'Completar con los pesos óptimos del perfil' carga la sugerencia del optimizador como punto de partida.",
                "Si los cambios cuestan más que tu efectivo, la app te dice cuánto dinero nuevo necesitarías.",
            ],
            "terms": [("Número efectivo de posiciones", "1 ÷ la suma de los pesos al cuadrado: qué tan diversificado está realmente el portafolio.")],
            "keep": ["Tu portafolio guardado nunca se modifica acá."],
        },
    },
}


def show(key: str) -> None:
    """Collapsible 'How to read this' box for a page or section."""
    entry = HELP.get(key)
    if not entry:
        return
    h = entry["es" if es() else "en"]
    labels = (("Qué ves", "Cómo leerlo", "Términos clave", "Tené en cuenta") if es()
              else ("What you see", "How to read it", "Key terms", "Keep in mind"))
    title = ("Ayuda: cómo leer " if es() else "Help: how to read ") + h["title"]
    with st.expander("ⓘ  " + title, expanded=False):
        steps = "".join(f"<li>{esc(x)}</li>" for x in h.get("how", []))
        terms = "".join(f"<div><dt>{esc(t)}</dt><dd>{esc(d)}</dd></div>" for t, d in h.get("terms", []))
        keep = "".join(f"<li>{esc(x)}</li>" for x in h.get("keep", []))
        st.html(f'<div class="mb-help"><div class="col"><div class="mb-sub">{labels[0]}</div><p>{esc(h["what"])}</p>'
                f'<div class="mb-sub">{labels[1]}</div><ol>{steps}</ol></div>'
                f'<div class="col">' + (f'<div class="mb-sub">{labels[2]}</div><dl>{terms}</dl>' if terms else "")
                + (f'<div class="mb-sub">{labels[3]}</div><ul>{keep}</ul>' if keep else "") + "</div></div>")
