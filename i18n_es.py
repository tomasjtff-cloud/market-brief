"""Spanish interface strings. Keys are the English text used in the code."""

ES: dict[str, str] = {
    # ---- navigation and shell
    "Markets": "Mercados", "News": "Noticias", "Map": "Mapa", "Watchlist": "Watchlist", "Compare": "Comparar",
    "Stock": "Acción", "Methodology": "Metodología",
    "Free markets terminal": "Terminal de mercados gratuita",
    "Search a company or ticker": "Buscar empresa o ticker",
    "Open {s}": "Abrir {s}",
    "No US-listed stock matches that search.": "Ninguna acción listada en EE.UU. coincide con la búsqueda.",
    "US 10Y": "Bono 10A EE.UU.",
    "Market status unavailable": "Estado del mercado no disponible",
    "US market open": "Mercado de EE.UU. abierto",
    "pre-market": "pre-apertura", "after hours": "post-cierre", "in {s}": "en {s}", "closed": "cerrado",
    "US market {state}, prices are the latest close": "Mercado de EE.UU. {state}; los precios son del último cierre",
    "New York": "Nueva York", "Mexico City": "Ciudad de México", "Buenos Aires": "Buenos Aires", "London": "Londres",
    # ---- index and market names
    "S&P 500": "S&P 500", "Nasdaq 100": "Nasdaq 100", "Dow Jones": "Dow Jones", "Russell 2000": "Russell 2000",
    "Gold": "Oro", "Crude oil": "Petróleo crudo", "Mexico": "México", "Argentina": "Argentina", "USA": "EE.UU.", "World": "Mundo",
    "via": "vía", "Live": "En vivo", "Close": "Cierre", "Today's low → high": "Mín. → máx. del día",
    # ---- sectors (SPDR and map)
    "Technology": "Tecnología", "Financials": "Financiero", "Health care": "Salud", "Consumer discretionary": "Consumo discrecional",
    "Communication services": "Comunicaciones", "Industrials": "Industria", "Consumer staples": "Consumo básico",
    "Energy": "Energía", "Utilities": "Servicios públicos", "Real estate": "Inmobiliario", "Materials": "Materiales",
    # ---- news desk sectors
    "Tech & AI": "Tecnología e IA", "Mining & metals": "Minería y metales", "Banks & finance": "Bancos y finanzas",
    "Consumer & retail": "Consumo y retail", "Industrials & autos": "Industria y autos", "Crypto": "Cripto",
    # ---- markets page
    "Mexico stocks (EWW)": "Acciones de México (EWW)", "Argentina stocks (ARGT)": "Acciones de Argentina (ARGT)",
    "Unavailable": "No disponible", "Dollar in Mexican pesos": "Dólar en pesos mexicanos", "As of {d}": "Al {d}",
    "Argentina official dollar": "Dólar oficial (Argentina)", "Argentina MEP dollar": "Dólar MEP (Argentina)",
    "Argentina blue dollar": "Dólar blue (Argentina)", "vs official": "vs oficial", "Sell": "Venta",
    "My watchlist": "Mi watchlist", "3 months": "3 meses", "Earnings coming up": "Próximos reportes",
    ", before open": ", antes de la apertura", ", after close": ", después del cierre",
    "What happened.": "Qué pasó.", "Why it matters.": "Por qué importa.", "Next to watch.": "Qué mirar.",
    "Sector performance today": "Desempeño por sector hoy", "SPDR sector ETFs": "ETFs sectoriales SPDR",
    "Sector data unavailable right now.": "Datos sectoriales no disponibles por ahora.",
    "US Treasury yield curve": "Curva de rendimientos del Tesoro de EE.UU.",
    "A negative spread (inverted curve) has often come before recessions.":
        "Un diferencial negativo (curva invertida) suele anticipar recesiones.",
    "Treasury yields unavailable right now.": "Rendimientos del Tesoro no disponibles por ahora.",
    "Mexico and Argentina": "México y Argentina",
    "Country stock markets through the US-listed ETFs that track them (EWW, ARGT). Argentine dollar rates from DolarApi.":
        "Bolsas de cada país a través de los ETFs listados en EE.UU. que las replican (EWW, ARGT). Cotizaciones del dólar en Argentina de DolarApi.",
    "The morning note": "La nota de la mañana", "Latest headlines": "Últimos titulares",
    "No answer this time from: ": "Sin respuesta esta vez de: ",
    "No headlines from the last day could be loaded. Try again in a few minutes.":
        "No se pudieron cargar titulares del último día. Probá de nuevo en unos minutos.",
    "Writing today's note from {n} headlines…": "Escribiendo la nota de hoy a partir de {n} titulares…",
    "Written by AI at {t} ET from {n} headlines and the market data on this page, and nothing else. Follow the source links before relying on it.":
        "Escrita por IA a las {t} ET a partir de {n} titulares y los datos de mercado de esta página, y nada más. Revisá las fuentes antes de basarte en ella.",
    "The AI note couldn't be written this time ({e}). The latest headlines are on the right.":
        "La nota de IA no se pudo escribir esta vez ({e}). Los últimos titulares están a la derecha.",
    # ---- map
    "Company": "Empresa", "Price": "Precio", "Change": "Variación", "Market cap": "Capitalización",
    "Market map": "Mapa del mercado",
    "The 25 largest US companies, sized by market value and colored by today's move":
        "Las 25 empresas más grandes de EE.UU., por tamaño según valor de mercado y color según el movimiento de hoy",
    "Loading quotes for the map…": "Cargando cotizaciones para el mapa…",
    "Quotes are unavailable right now. Try again in a minute.": "Cotizaciones no disponibles por ahora. Probá en un minuto.",
    "Green is up and red is down, capped at ±3% for color. Click a ticker in the tables to open it.":
        "Verde sube y rojo baja; el color se satura en ±3%. Hacé clic en un ticker de las tablas para abrirlo.",
    "Top gainers": "Mayores alzas", "Top decliners": "Mayores bajas", "Sectors": "Sectores", "Sector ETF": "ETF sectorial",
    # ---- watchlist
    "Price, performance, risk and value side by side. Click a ticker to open it.":
        "Precio, rendimiento, riesgo y valor lado a lado. Hacé clic en un ticker para abrirlo.",
    "DCF needs positive free cash flow and SEC filings": "El DCF necesita flujo de caja libre positivo y reportes a la SEC",
    "Today": "Hoy", "1M": "1M", "3M": "3M", "YTD": "En el año", "1Y": "1A", "Volatility": "Volatilidad", "Beta": "Beta",
    "Max DD": "Caída máx.", "52-week range": "Rango 52 semanas", "6 months": "6 meses", "P/E": "P/U",
    "DCF value": "Valor DCF", "Upside": "Potencial", "Earnings": "Reporte",
    "Volatility, beta (2 years of weekly returns vs SPY) and max drawdown are calculated here. DCF value is the base case with default assumptions (5-year revenue CAGR capped at 0 to 20%, CAPM cost of equity, 2.5% terminal growth); open a stock to change them. P/E is trailing twelve months from Finnhub.":
        "La volatilidad, la beta (2 años de rendimientos semanales vs SPY) y la caída máxima se calculan acá. El valor DCF es el caso base con supuestos por defecto (CAGR de ingresos de 5 años limitado entre 0 y 20%, costo del capital por CAPM, crecimiento terminal de 2.5%); abrí una acción para cambiarlos. El P/U es de los últimos doce meses, de Finnhub.",
    "Manage the list": "Administrar la lista", "Remove {t}": "Quitar {t}", "Add a stock": "Agregar una acción",
    "Company or ticker": "Empresa o ticker", "Match": "Coincidencia", "Add {s}": "Agregar {s}",
    "The list holds {n} stocks.": "La lista admite {n} acciones.",
    "The list is saved in this page's address. Bookmark it to keep it.":
        "La lista se guarda en la dirección de esta página. Guardala en favoritos para conservarla.",
    # ---- compare
    "Performance, risk and correlation of any stocks against the market":
        "Rendimiento, riesgo y correlación de cualquier acción contra el mercado",
    "Tickers (up to 6)": "Tickers (hasta 6)", "Period": "Período", "Pick at least one ticker.": "Elegí al menos un ticker.",
    "No price history right now for: ": "Sin historial de precios por ahora para: ",
    "Equal-weight portfolio": "Portafolio de pesos iguales", "Series": "Serie", "Return": "Rendimiento",
    "Annualized": "Anualizado", "Sharpe": "Sharpe", "Max drawdown": "Caída máxima", "Beta vs SPY": "Beta vs SPY",
    "Over the selected period. Sharpe uses the 10-year Treasury as the risk-free rate; beta uses two years of weekly returns. The equal-weight portfolio holds the chosen stocks (not SPY) in equal parts, rebalanced daily.":
        "En el período elegido. El Sharpe usa el bono del Tesoro a 10 años como tasa libre de riesgo; la beta usa dos años de rendimientos semanales. El portafolio de pesos iguales tiene las acciones elegidas (sin SPY) en partes iguales, rebalanceado a diario.",
    "Correlation of daily returns": "Correlación de rendimientos diarios", "How to read it": "Cómo leerlo",
    "Correlation runs from −1 to +1. Stocks near +1 move together, so holding both adds little diversification; values near 0 or negative smooth a portfolio's ride. Compare the equal-weight portfolio's volatility with the average of the single stocks to see how much diversification is helping.":
        "La correlación va de −1 a +1. Las acciones cerca de +1 se mueven juntas, así que tener ambas diversifica poco; valores cerca de 0 o negativos suavizan el portafolio. Compará la volatilidad del portafolio de pesos iguales con el promedio de las acciones individuales para ver cuánto ayuda la diversificación.",
    # ---- methodology
    "Where every number comes from and how it is calculated": "De dónde sale cada número y cómo se calcula",
    "Every figure is tagged: {mkt} prices and rates from data providers, {rep} numbers companies filed with the SEC, {calc} figures computed here, {ana} sell-side analyst ratings and {ai} text written by the AI from the data shown.":
        "Cada dato está etiquetado: {mkt} precios y tasas de proveedores de datos, {rep} cifras que las empresas reportaron a la SEC, {calc} cálculos hechos acá, {ana} recomendaciones de analistas y {ai} texto escrito por la IA a partir de los datos mostrados.",
    # ---- stock page
    "Summary": "Resumen", "Chart": "Gráfico", "Financials": "Finanzas", "Valuation": "Valuación", "Outlook": "Escenarios",
    "Analysts & AI take": "Analistas y opinión IA",
    "Area": "Área", "Candles": "Velas",
    "Intraday bars aren't available right now; showing one month instead.":
        "Las barras intradía no están disponibles; se muestra un mes.",
    "5-minute bars": "barras de 5 minutos", "30-minute bars": "barras de 30 minutos", "daily bars": "barras diarias",
    "{r} change": "Variación {r}", "from Twelve Data": "de Twelve Data",
    "No quote found for {t}. Check the ticker or search for the company in the top bar.":
        "No se encontró cotización para {t}. Revisá el ticker o buscá la empresa en la barra de arriba.",
    "Price history for {t} isn't available right now. Try again in a minute.":
        "El historial de precios de {t} no está disponible por ahora. Probá en un minuto.",
    "Market open": "Mercado abierto", "At close": "Al cierre",
    "✓ In watchlist": "✓ En watchlist", "Click to remove from the watchlist": "Clic para quitar de la watchlist",
    "+ Add to watchlist": "+ Agregar a watchlist",
    "P/E (TTM)": "P/U (12M)", "EPS (TTM)": "UPA (12M)", "1 year": "1 año",
    "Previous close": "Cierre anterior", "Day's range": "Rango del día", "Volume (last day)": "Volumen (último día)",
    "Avg. volume (3M)": "Volumen prom. (3M)", "Beta (2Y weekly)": "Beta (2A semanal)", "Dividend yield": "Rendimiento por dividendo",
    "None": "Ninguno", "Next earnings": "Próximo reporte", "Sharpe (1Y)": "Sharpe (1A)", "Key statistics": "Estadísticas clave",
    "1 month": "1 mes", "3 years": "3 años", "5 years": "5 años",
    "Performance vs S&amp;P 500": "Rendimiento vs S&amp;P 500", "Difference": "Diferencia",
    "Analyst ratings": "Recomendaciones de analistas",
    "Consensus <b>{l}</b> ({s} / 5) from {n} analysts, {b} buy or strong buy ({p}). Sell-side ratings lean positive in general.":
        "Consenso <b>{l}</b> ({s} / 5) de {n} analistas, {b} en compra o compra fuerte ({p}). Las recomendaciones de los bancos suelen ser optimistas.",
    "No analyst ratings available.": "No hay recomendaciones de analistas.",
    "50-day average": "Promedio de 50 días", "200-day average": "Promedio de 200 días",
    "52-week high": "Máximo de 52 semanas", "52-week low": "Mínimo de 52 semanas",
    "Key levels": "Niveles clave", "Level": "Nivel", "Price vs level": "Precio vs nivel", "Profile": "Perfil",
    "Industry": "Industria", "Country": "País", "Listed since": "Cotiza desde", "Website": "Sitio web",
    "50-day": "50 días", "200-day": "200 días", "±1σ range ahead": "Rango ±1σ a futuro",
    "How far it usually moves": "Cuánto suele moverse", "Horizon": "Horizonte",
    "2 in 3 outcomes": "2 de cada 3 casos", "19 in 20 outcomes": "19 de cada 20 casos",
    "Normal model on last year's volatility ({v} a year), no drift. The Outlook section uses real past moves instead.":
        "Modelo normal con la volatilidad del último año ({v} anual), sin tendencia. La sección Escenarios usa movimientos reales del pasado.",
    "Max drawdown, 1Y": "Caída máxima, 1A", "Sharpe, 1Y": "Sharpe, 1A", "RSI (14)": "RSI (14)",
    "Drawdown, last year": "Caída desde máximos, último año",
    "Reading SEC filings…": "Leyendo los reportes a la SEC…",
    "Reported financials aren't available for {t} (non-US filers, ETFs and funds don't file 10-Ks).":
        "No hay estados financieros reportados para {t} (las empresas no estadounidenses, los ETFs y los fondos no presentan 10-K).",
    "Revenue": "Ingresos", "Revenue growth": "Crecimiento de ingresos", "Gross profit": "Utilidad bruta",
    "Operating income": "Utilidad operativa", "Net income": "Utilidad neta", "Diluted EPS": "UPA diluida",
    "Operating cash flow": "Flujo de caja operativo", "Capital expenditures": "Inversión de capital (capex)",
    "Free cash flow": "Flujo de caja libre", "Gross margin": "Margen bruto", "Operating margin": "Margen operativo",
    "Net margin": "Margen neto", "FCF margin": "Margen de FCF", "Annual financials": "Finanzas anuales", "Fiscal year": "Año fiscal",
    "From 10-K filings (XBRL), calendar-aligned fiscal years. Balance sheet as of {d}: cash and short-term investments {c}, debt {debt}, net debt {nd}.":
        "De los reportes 10-K (XBRL), años fiscales alineados al calendario. Balance al {d}: caja e inversiones de corto plazo {c}, deuda {debt}, deuda neta {nd}.",
    "Note: ": "Nota: ", "Revenue, profit and cash": "Ingresos, utilidad y caja", "Margins": "Márgenes",
    "Gross": "Bruto", "Operating": "Operativo", "Net": "Neto",
    "A DCF isn't available for {t}: it needs SEC filings with free cash flow and a share count (non-US companies, ETFs and funds aren't covered).":
        "No hay DCF para {t}: necesita reportes a la SEC con flujo de caja libre y cantidad de acciones (no cubre empresas no estadounidenses, ETFs ni fondos).",
    "DCF assumptions — change them and everything below updates": "Supuestos del DCF: cambialos y todo lo de abajo se actualiza",
    "Starting free cash flow": "Flujo de caja libre inicial", "Latest year": "Último año", "3-year average": "Promedio de 3 años",
    "FCF growth, years 1 to 5 (%)": "Crecimiento del FCF, años 1 a 5 (%)", "Terminal growth (%)": "Crecimiento terminal (%)",
    "Equity risk premium (%)": "Prima de riesgo de mercado (%)", "Pre-tax cost of debt (%)": "Costo de la deuda antes de impuestos (%)",
    "Tax rate (%)": "Tasa de impuestos (%)", "Discount rate used (WACC, %)": "Tasa de descuento usada (WACC, %)",
    "Starting FCF {fcf}. Default growth = last five years' revenue CAGR ({g}) capped at 0 to 20%; years 6 to 10 fade to terminal growth. Cost of equity {rf} + {b} × {erp} = {ke}; weights {we} equity / {wd} debt; WACC {w}. {rfl}.":
        "FCF inicial {fcf}. Crecimiento por defecto = CAGR de ingresos de los últimos cinco años ({g}) limitado entre 0 y 20%; en los años 6 a 10 converge al crecimiento terminal. Costo del capital {rf} + {b} × {erp} = {ke}; pesos {we} capital / {wd} deuda; WACC {w}. {rfl}.",
    "Free cash flow is negative, so a cash-flow DCF doesn't apply. Revenue growth and the path to profitability are the better lens.":
        "El flujo de caja libre es negativo, así que un DCF por flujos no aplica. Conviene mirar el crecimiento de ingresos y el camino a la rentabilidad.",
    "Intrinsic value per share": "Valor intrínseco por acción", "Bear": "Pesimista", "Bull": "Optimista",
    "Market price": "Precio de mercado", "Upside to intrinsic value": "Potencial hasta el valor intrínseco",
    "Verdict under these assumptions": "Veredicto con estos supuestos",
    "Looks undervalued": "Parece subvaluada", "Looks overvalued": "Parece sobrevaluada", "Roughly fairly valued": "Valuada aproximadamente justa",
    "Within ±15% counts as fairly valued": "Dentro de ±15% se considera valuación justa",
    "<b>What the price implies.</b> To be worth ${p}, free cash flow would need to grow about <b>{g} a year for five years</b>, then fade to {gt}, at a {d} discount rate. Revenue grew {h} a year over the last five years.":
        "<b>Qué implica el precio.</b> Para valer ${p}, el flujo de caja libre tendría que crecer cerca de <b>{g} anual durante cinco años</b> y luego converger a {gt}, con una tasa de descuento de {d}. Los ingresos crecieron {h} anual en los últimos cinco años.",
    "Valuation ranges (football field)": "Rangos de valuación (football field)",
    "DCF scenarios, bear to bull": "Escenarios DCF, pesimista a optimista", "DCF sensitivity (WACC ±1, g ±0.5)": "Sensibilidad DCF (WACC ±1, g ±0.5)",
    "52-week trading range": "Rango de cotización 52 semanas", "3-month statistical range": "Rango estadístico a 3 meses",
    "Bear: growth 5 points lower, discount rate 1 point higher. Bull: the opposite.":
        "Pesimista: crecimiento 5 puntos menor y tasa de descuento 1 punto mayor. Optimista: lo contrario.",
    "Sensitivity table and DCF detail": "Tabla de sensibilidad y detalle del DCF",
    "**Intrinsic value per share** — rows: discount rate, columns: terminal growth":
        "**Valor intrínseco por acción**: filas = tasa de descuento, columnas = crecimiento terminal",
    "Year": "Año", "Growth": "Crecimiento", "FCF": "FCF", "Discount factor": "Factor de descuento", "PV of FCF": "VP del FCF",
    "Discounted FCF {a} + discounted terminal value {b} = EV {ev}; − net debt {nd} = equity {eq}; ÷ {sh}B shares = ${ps}. Terminal value is {ts} of EV.":
        "FCF descontado {a} + valor terminal descontado {b} = EV {ev}; − deuda neta {nd} = capital {eq}; ÷ {sh} mil M de acciones = ${ps}. El valor terminal es {ts} del EV.",
    "Multiples": "Múltiplos", "FCF yield": "Rendimiento de FCF",
    "No trend": "Sin tendencia", "Market average (+8%/yr)": "Promedio del mercado (+8%/año)",
    "Recent trend (capped ±30%/yr)": "Tendencia reciente (tope ±30%/año)", "Trend assumption": "Supuesto de tendencia",
    "Simulating 4,000 scenarios…": "Simulando 4,000 escenarios…",
    "Not enough price history to simulate scenarios.": "No hay historial suficiente para simular escenarios.",
    "of scenarios end the 6 months above today's close": "de los escenarios terminan los 6 meses arriba del cierre de hoy",
    "of scenarios fall 20% or more at some point": "de los escenarios caen 20% o más en algún momento",
    "of scenarios reach the 52-week high (${v})": "de los escenarios llegan al máximo de 52 semanas (${v})",
    "of scenarios touch the DCF value (${v})": "de los escenarios tocan el valor DCF (${v})",
    "Model probabilities over 6 months": "Probabilidades del modelo a 6 meses",
    "Bad": "Malo", "Weak": "Débil", "Middle": "Medio", "Good": "Bueno", "Very good": "Muy bueno", "{p}th pct": "percentil {p}",
    "Scenario table": "Tabla de escenarios", "How this works": "Cómo funciona",
    "4,000 six-month paths. Each simulated day replays a real daily move of {t} from the last two years, so crash days and rallies keep their real frequency. The trend assumption replaces the average move. These are <b>model probabilities, not forecasts</b>: they assume the next six months look like a reshuffled version of the past two years.":
        "4,000 trayectorias a seis meses. Cada día simulado repite un movimiento diario real de {t} de los últimos dos años, así que los desplomes y los rallies mantienen su frecuencia real. El supuesto de tendencia reemplaza el movimiento promedio. Son <b>probabilidades del modelo, no pronósticos</b>: suponen que los próximos seis meses se parecen a una versión mezclada de los últimos dos años.",
    "Compare with": "Comparar con", "Correlation with {t}": "Correlación con {t}",
    'More options on the <a href="{u}" target="_self">Compare</a> page, including an equal-weight portfolio.':
        'Más opciones en la página <a href="{u}" target="_self">Comparar</a>, incluido un portafolio de pesos iguales.',
    "No company news in the last 7 days.": "No hay noticias de la empresa en los últimos 7 días.",
    "Latest news on {t}": "Últimas noticias de {t}",
    # ---- analysts & AI take
    "Strong Buy": "Compra fuerte", "Buy": "Compra", "Hold": "Mantener", "Strong Sell": "Venta fuerte",
    "Strong buy": "Compra fuerte", "Strong sell": "Venta fuerte",
    "What the experts say": "Qué dicen los expertos", "Wall Street consensus": "Consenso de Wall Street",
    "Finnhub recommendation trends": "Tendencias de recomendación de Finnhub",
    "No analyst ratings available for {t}.": "No hay recomendaciones de analistas para {t}.",
    "more bullish": "más optimista", "more bearish": "más pesimista", "unchanged": "sin cambios", "vs": "vs",
    "analysts": "analistas",
    "Ratings from the brokerage analysts that cover the stock, aggregated monthly by Finnhub (5 = strong buy, 1 = strong sell). Price targets are not in the free plan.":
        "Recomendaciones de los analistas de bancos y brokers que cubren la acción, agregadas mensualmente por Finnhub (5 = compra fuerte, 1 = venta fuerte). Los precios objetivo no están en el plan gratuito.",
    "Model view": "Visión del modelo", "AI take": "Opinión de la IA", "Gemini reads the data on this page": "Gemini lee los datos de esta página",
    "Agrees with Wall Street": "Coincide con Wall Street", "Differs from Wall Street": "Difiere de Wall Street",
    "Conviction": "Convicción", "Low": "Baja", "Medium": "Media", "High": "Alta",
    "Model opinion from the data in this app, written {d} ET. Not investment advice.":
        "Opinión del modelo a partir de los datos de esta app, escrita el {d} ET. No es asesoría de inversión.",
    "Vs the consensus.": "Frente al consenso.",
    "Click the button for a written take with a <b>Buy / Hold / Sell</b> lean, compared against the Wall Street consensus, plus bull, base and bear cases, risks and catalysts.":
        "Hacé clic en el botón para obtener una opinión escrita con una postura de <b>Compra / Mantener / Venta</b>, comparada con el consenso de Wall Street, más casos optimista, base y pesimista, riesgos y catalizadores.",
    "It uses the <b>DCF assumptions set in the Valuation tab</b>.": "Usa los <b>supuestos del DCF de la pestaña Valuación</b>.",
    "It uses the default DCF assumptions; open the Valuation tab and adjust them first to use yours.":
        "Usa los supuestos del DCF por defecto; abrí la pestaña Valuación y ajustalos antes para usar los tuyos.",
    "Data: fetched from the sources · Calc: computed by the app · AI: model opinion.":
        "Datos: obtenidos de las fuentes · Cálculos: hechos por la app · IA: opinión del modelo.",
    "Refresh AI take": "Actualizar opinión IA", "Generate AI take": "Generar opinión IA",
    "Collecting the data and writing the take… (10 to 30 seconds)": "Reuniendo los datos y escribiendo la opinión… (10 a 30 segundos)",
    "The AI take couldn't be written this time: {e}": "La opinión de la IA no se pudo escribir esta vez: {e}",
    "Where it stands": "Situación", "Recent performance": "Desempeño reciente", "Fundamentals": "Fundamentales",
    "News flow": "Noticias", "Bear case": "Caso pesimista", "Base case": "Caso base", "Bull case": "Caso optimista",
    "Full AI analysis": "Análisis completo de la IA", "Main risks": "Principales riesgos", "Coming catalysts": "Próximos catalizadores",
    "Conclusion.": "Conclusión.",
    "Not investment advice · statistics describe the past, they don't predict the future.":
        "No es asesoría de inversión · las estadísticas describen el pasado, no predicen el futuro.",
    # ---- news desk
    "Positive": "Positivo", "Mixed": "Mixto", "Negative": "Negativo", "No read": "Sin lectura",
    "No recent headlines in this section.": "No hay titulares recientes en esta sección.",
    "USD/MXN (live)": "USD/MXN (en vivo)", "ECB {d} · 1 week {w}": "BCE {d} · 1 semana {w}", "ECB {d}": "BCE {d}",
    "US dollar index (UUP)": "Índice dólar (UUP)", "ETF proxy": "vía ETF",
    "Official": "Oficial", "Wholesale": "Mayorista", "MEP": "MEP", "CCL": "CCL", "Blue": "Blue",
    "gap": "brecha", "Dollar {n}": "Dólar {n}", "Country risk (EMBI)": "Riesgo país (EMBI)",
    "Fed funds (effective)": "Tasa de la Fed (efectiva)", "US 2-year": "EE.UU. 2 años", "US 10-year": "EE.UU. 10 años",
    "US 30-year": "EE.UU. 30 años", "change vs 1 week": "cambio vs 1 semana", "10Y − 2Y spread": "Diferencial 10A − 2A",
    "Negative = inverted curve": "Negativo = curva invertida",
    "The dollar": "El dólar", "Interest rates": "Tasas de interés",
    "AI read unavailable right now; the headlines are below.": "Lectura de la IA no disponible por ahora; los titulares están abajo.",
    "What to watch.": "Qué mirar.", "AI read": "Lectura IA",
    "News desk": "Mesa de noticias",
    "Headlines by region and by sector from official publisher feeds, exchange rates and interest rates, and an AI read of what it means for markets.":
        "Titulares por región y por sector de los feeds oficiales de cada medio, tipos de cambio y tasas de interés, y una lectura de la IA sobre qué significa para los mercados.",
    "Collecting headlines from about 20 sources…": "Reuniendo titulares de unas 20 fuentes…",
    "Writing the AI read of today's news… (20 to 40 seconds the first time)": "Escribiendo la lectura de la IA de las noticias de hoy… (20 a 40 segundos la primera vez)",
    "Written {d} ET from {n} headlines; refreshed every 3 hours.": "Escrita el {d} ET a partir de {n} titulares; se actualiza cada 3 horas.",
    "Today’s read": "La lectura de hoy",
    "The AI read couldn't be written this time ({e}). Headlines and data are below.":
        "La lectura de la IA no se pudo escribir esta vez ({e}). Los titulares y los datos están abajo.",
    "Exchange rates and interest rates": "Tipos de cambio y tasas de interés", "FX and rates": "Tipo de cambio y tasas",
    "AI read unavailable right now.": "Lectura de la IA no disponible por ahora.",
    "By region": "Por región", "By sector": "Por sector", "headline": "titular", "headlines": "titulares",
    "Tagged by keywords, all regions": "Clasificados por palabras clave, todas las regiones",
    "Unavailable right now: {f}.": "No disponibles por ahora: {f}.",
    "Headlines from the publishers' official RSS feeds and Finnhub, refreshed every 30 minutes, last {h} hours, duplicates removed. Sectors are assigned by keywords (English and Spanish), so a headline can appear in more than one. ECB reference rates via Frankfurter; Argentina rates via DolarApi and ArgentinaDatos; US rates via FRED.":
        "Titulares de los feeds RSS oficiales de cada medio y de Finnhub, actualizados cada 30 minutos, últimas {h} horas, sin duplicados. Los sectores se asignan por palabras clave (inglés y español), así que un titular puede aparecer en más de uno. Tipos de cambio de referencia del BCE vía Frankfurter; cotizaciones de Argentina vía DolarApi y ArgentinaDatos; tasas de EE.UU. vía FRED.",
    # ---- charts
    "{n}-day avg": "Prom. {n} días", "Upper band": "Banda superior", "Lower band": "Banda inferior", "Upper": "Superior",
    "Lower": "Inferior", "Prev close {v}": "Cierre ant. {v}", "Volume": "Volumen", "9 in 10 scenarios": "9 de cada 10 escenarios",
    "Middle half of scenarios": "Mitad central de escenarios", "Median path": "Trayectoria mediana", "Median": "Mediana",
    "A month ago": "Hace un mes", "Latest ({d})": "Último ({d})", "Latest": "Último",
}

METHOD_ES = """
#### Fuentes de datos (todas en planes gratuitos)
| Qué | Fuente | Frecuencia |
|---|---|---|
| Cotizaciones, rango del día, búsqueda, perfil de la empresa, métricas clave, recomendaciones de analistas, noticias, fechas de reportes | Finnhub | Cotizaciones cada minuto; el resto de cada hora a diario |
| Historial de precios diario e intradía, volumen, USD/MXN | Twelve Data | Barras diarias cada 6 horas, intradía cada 5 minutos |
| Estados financieros | SEC EDGAR (XBRL company facts) | Según los reportes 10-K y 10-Q |
| Rendimientos del Tesoro (1 mes a 30 años) y tasa de la Fed | FRED, Fed de St. Louis | Diario, día hábil anterior |
| Bitcoin | CoinGecko | Cada 10 minutos aprox. |
| Dólar en Argentina | DolarApi | Cada 15 minutos aprox. |
| Riesgo país de Argentina (EMBI) | ArgentinaDatos | Diario |
| Tipos de cambio contra el dólar | Tipos de referencia del BCE vía Frankfurter | Diario |
| Titulares de EE.UU. | CNBC, MarketWatch, WSJ Markets, Reserva Federal (RSS) y Finnhub | Cada 30 minutos |
| Titulares de México | El Financiero (economía, mercados y empresas), Expansión, El Economista (RSS) | Cada 30 minutos |
| Titulares de Argentina | Ámbito (economía y finanzas), Infobae economía (RSS) | Cada 30 minutos |
| Titulares del mundo y por sector | BBC Business, CNBC World, DW Business, Mining.com, TechCrunch AI, OilPrice, CoinDesk (RSS), noticias de Finnhub (forex, M&A y cripto) | Cada 30 minutos |

Los índices se muestran a través de los ETFs que los replican (SPY, QQQ, DIA, IWM; EWW para México, ARGT para Argentina),
porque los niveles de los índices no vienen en los planes gratuitos. Un limitador compartido mantiene la app dentro de los
límites por minuto de cada proveedor.

#### Mesa de noticias
Los titulares se agrupan por región según el medio del que vienen, y por sector con una lista de palabras clave en inglés y
español (un titular puede estar en más de un sector). La lectura de la IA se escribe a partir de esos titulares y de los datos
de tipos de cambio y tasas de la página, cada 3 horas, y asigna a cada región y sector un tono: positivo, mixto o negativo.

#### Riesgo y rendimiento
La volatilidad es el desvío estándar anualizado de los rendimientos logarítmicos diarios del último año. La beta es la
pendiente de los rendimientos semanales contra SPY en dos años. El Sharpe es el rendimiento menos la tasa del bono a 10 años,
dividido por la volatilidad. La caída máxima es la peor baja desde un máximo. El RSI es el índice de fuerza relativa de 14
días; las bandas de Bollinger son el promedio de 20 días ± dos desvíos estándar.

#### Escenarios (simulación)
4,000 trayectorias a seis meses. Cada día simulado repite un movimiento diario real de la acción de los últimos dos años
(bootstrap), así que los desplomes y los rallies mantienen su proporción real. El movimiento diario promedio se reemplaza por la
tendencia elegida: ninguna, el promedio de largo plazo del mercado (cerca de 8% anual) o la tendencia reciente de la acción con
tope de ±30% anual. Los percentiles de las trayectorias forman la tabla de escenarios; la proporción de trayectorias que cruzan
un nivel da cada probabilidad. Son probabilidades del modelo que suponen que los próximos seis meses se parecen a una versión
mezclada de los últimos dos años. No son pronósticos.

#### DCF y valuación
El flujo de caja libre (flujo operativo menos inversión de capital) de los reportes a la SEC crece a la tasa elegida durante
cinco años, converge al crecimiento terminal en los cinco siguientes y luego se suma un valor terminal de Gordon. La tasa de
descuento es el WACC: costo del capital por CAPM (bono a 10 años + beta × prima de riesgo de mercado), costo de la deuda después
de impuestos y pesos a valor de mercado. El valor del capital es el valor de la empresa menos la deuda neta, por acción. El DCF
inverso calcula el crecimiento que implica el precio actual. El football field compara escenarios DCF, sensibilidad, el rango
de 52 semanas y el rango estadístico contra el precio.

#### Recomendaciones de analistas
Las tendencias mensuales de Finnhub se promedian en una escala de 1 (venta fuerte) a 5 (compra fuerte): 4.5+ compra fuerte,
3.5+ compra, 2.5+ mantener, 1.5+ venta, debajo de eso venta fuerte, con el cambio contra tres meses antes.

#### IA
Google Gemini escribe la nota de la mañana, la lectura de la mesa de noticias y el análisis de cada acción solo con los datos
que muestra la app, con instrucciones de no agregar hechos ni fijar precios objetivo. La opinión de cada acción da una postura de
Compra / Mantener / Venta, marcada como opinión del modelo. La app elige un modelo Gemini rápido disponible y cambia si alguno
está saturado.

#### Límites
Los datos gratuitos pueden tener demora o fallar por momentos; cada número muestra su horario. La cobertura de la SEC varía
por empresa. Nada de esto es asesoría de inversión.
"""
