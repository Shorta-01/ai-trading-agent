"""V1 universe registry — locked in `version-1-product-experience-locks.md §21.6`.

Static Python tables listing the tickers the daily scan iterates over.
Each entry carries:

* ``symbol`` — the exchange-local ticker (e.g. ``"ASML"``, ``"AAPL"``)
* ``eodhd_symbol`` — the EODHD-formatted symbol (``"ASML.AS"``,
  ``"AAPL.US"``) used by the fundamentals + bars endpoints
* ``index_code`` — the index the ticker belongs to (e.g. ``"BEL20"``)
* ``sector`` — best-effort sector hint for the QVM cross-section;
  EODHD's `Sector` field overrides this when available
* ``country_code`` — V1.1 §22.4 addition. Two-letter ISO code (e.g.
  ``"BE"``, ``"US"``) so the Stoxx 600 cross-country aggregation
  works cleanly. ``None`` when not known.

V1.1 §22.4 lock adds operator-selectable universe sets:

* ``SP500`` (default) — the V1 hand-curated ~325-ticker set covering
  Bel20 + AEX + CAC40 + DAX40 + S&P 100 + NASDAQ100 extras. Kept
  for backward compatibility.
* ``EU600`` — V1 set + representative Stoxx 600 additions (UK FTSE
  100 top names, Swiss SLI top names, IBEX 35 top names, FTSE MIB
  top names, Stoxx Nordic 30 names) so the morning chain can scan
  a broader EU universe.
* ``ALL_5K`` — superset of the above plus a representative US small-
  / mid-cap sample. The "full" 5 000-ticker materialisation
  requires the EODHD bulk-list endpoint — that resolution is a
  post-V1.1 widening; the in-process registry stays representative
  so the operator surface is locked from Slice 31 forward without
  bloating the Python module.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class UniverseEntry:
    symbol: str
    eodhd_symbol: str
    index_code: str
    sector: str | None = None
    country_code: str | None = None


# V1.1 §22.4 operator-selectable universe sets.
UNIVERSE_SET_STARTER_50: Final[str] = "STARTER_50"
UNIVERSE_SET_SP500: Final[str] = "SP500"
UNIVERSE_SET_EU600: Final[str] = "EU600"
UNIVERSE_SET_ALL_5K: Final[str] = "ALL_5K"
LOCKED_UNIVERSE_SETS: Final[frozenset[str]] = frozenset(
    {
        UNIVERSE_SET_STARTER_50,
        UNIVERSE_SET_SP500,
        UNIVERSE_SET_EU600,
        UNIVERSE_SET_ALL_5K,
    }
)
# V1.2 §BS / GAPS.md P1-4 update: SP500 is de nieuwe default zodat
# de orchestrator-scan op een breed US large-cap universum (~325
# namen) draait wanneer de operator de scan inschakelt. CLAUDE.md §5
# vraagt namelijk een "autonoom universum-scan" over ~3500 namen —
# STARTER_50 (45 namen, alleen Bel20+AEX) dekt dit doctrine-beeld
# duidelijk niet. SP500 is een pragmatische tussenstop: groot genoeg
# voor zinvolle daily-opportunity scanning, klein genoeg om de
# EODHD-quota niet meteen op te eten.
#
# Operator die het volledige doctrine-doel wil bereiken kiest
# expliciet EU600 (~450 namen, incl. Stoxx 600) of ALL_5K
# (volledige scope). Operator die met een conservatievere set wil
# starten kan handmatig STARTER_50 selecteren via
# /instellingen → Beleggingsuniversum.
#
# De scan blijft disabled-by-default (``universe_scan_sync_enabled =
# False``); het wijzigen van de default-SET treft alleen wat er
# gescand wordt zodra de operator inschakelt.
DEFAULT_UNIVERSE_SET: Final[str] = UNIVERSE_SET_SP500


# ---- Bel20 -----------------------------------------------------------

BEL20: Final[tuple[UniverseEntry, ...]] = (
    UniverseEntry("ABI", "ABI.BR", "BEL20", "Consumer Staples"),
    UniverseEntry("ACKB", "ACKB.BR", "BEL20", "Financials"),
    UniverseEntry("AED", "AED.BR", "BEL20", "Real Estate"),
    UniverseEntry("AGS", "AGS.BR", "BEL20", "Financials"),
    UniverseEntry("APAM", "APAM.BR", "BEL20", "Financials"),
    UniverseEntry("ARGX", "ARGX.BR", "BEL20", "Healthcare"),
    UniverseEntry("AZE", "AZE.BR", "BEL20", "Industrials"),
    UniverseEntry("COFB", "COFB.BR", "BEL20", "Financials"),
    UniverseEntry("DIE", "DIE.BR", "BEL20", "Consumer Discretionary"),
    UniverseEntry("ELI", "ELI.BR", "BEL20", "Utilities"),
    UniverseEntry("GBLB", "GBLB.BR", "BEL20", "Financials"),
    UniverseEntry("KBC", "KBC.BR", "BEL20", "Financials"),
    UniverseEntry("LOTB", "LOTB.BR", "BEL20", "Consumer Staples"),
    UniverseEntry("PROX", "PROX.BR", "BEL20", "Communication Services"),
    UniverseEntry("SOF", "SOF.BR", "BEL20", "Industrials"),
    UniverseEntry("SOLB", "SOLB.BR", "BEL20", "Materials"),
    UniverseEntry("UCB", "UCB.BR", "BEL20", "Healthcare"),
    UniverseEntry("UMI", "UMI.BR", "BEL20", "Materials"),
    UniverseEntry("VLP", "VLP.BR", "BEL20", "Industrials"),
    UniverseEntry("WDP", "WDP.BR", "BEL20", "Real Estate"),
)


# ---- AEX 25 ----------------------------------------------------------

AEX: Final[tuple[UniverseEntry, ...]] = (
    UniverseEntry("ADYEN", "ADYEN.AS", "AEX", "Financials"),
    UniverseEntry("AGN", "AGN.AS", "AEX", "Financials"),
    UniverseEntry("AKZA", "AKZA.AS", "AEX", "Materials"),
    UniverseEntry("MT", "MT.AS", "AEX", "Materials"),
    UniverseEntry("ASM", "ASM.AS", "AEX", "Technology"),
    UniverseEntry("ASML", "ASML.AS", "AEX", "Technology"),
    UniverseEntry("ASRNL", "ASRNL.AS", "AEX", "Financials"),
    UniverseEntry("BESI", "BESI.AS", "AEX", "Technology"),
    UniverseEntry("DSFIR", "DSFIR.AS", "AEX", "Healthcare"),
    UniverseEntry("EXO", "EXO.AS", "AEX", "Industrials"),
    UniverseEntry("HEIA", "HEIA.AS", "AEX", "Consumer Staples"),
    UniverseEntry("IMCD", "IMCD.AS", "AEX", "Materials"),
    UniverseEntry("INGA", "INGA.AS", "AEX", "Financials"),
    UniverseEntry("KPN", "KPN.AS", "AEX", "Communication Services"),
    UniverseEntry("NN", "NN.AS", "AEX", "Financials"),
    UniverseEntry("PHIA", "PHIA.AS", "AEX", "Healthcare"),
    UniverseEntry("PRX", "PRX.AS", "AEX", "Communication Services"),
    UniverseEntry("RAND", "RAND.AS", "AEX", "Industrials"),
    UniverseEntry("REN", "REN.AS", "AEX", "Industrials"),
    UniverseEntry("SHELL", "SHELL.AS", "AEX", "Energy"),
    UniverseEntry("UMG", "UMG.AS", "AEX", "Communication Services"),
    UniverseEntry("UNA", "UNA.AS", "AEX", "Consumer Staples"),
    UniverseEntry("WKL", "WKL.AS", "AEX", "Industrials"),
    UniverseEntry("AD", "AD.AS", "AEX", "Consumer Staples"),
    UniverseEntry("VPK", "VPK.AS", "AEX", "Industrials"),
)


# ---- CAC 40 ----------------------------------------------------------

CAC40: Final[tuple[UniverseEntry, ...]] = (
    UniverseEntry("AC", "AC.PA", "CAC40", "Consumer Discretionary"),
    UniverseEntry("AI", "AI.PA", "CAC40", "Materials"),
    UniverseEntry("AIR", "AIR.PA", "CAC40", "Industrials"),
    UniverseEntry("ALO", "ALO.PA", "CAC40", "Industrials"),
    UniverseEntry("MT", "MT.PA", "CAC40", "Materials"),
    UniverseEntry("CS", "CS.PA", "CAC40", "Financials"),
    UniverseEntry("BNP", "BNP.PA", "CAC40", "Financials"),
    UniverseEntry("EN", "EN.PA", "CAC40", "Industrials"),
    UniverseEntry("CAP", "CAP.PA", "CAC40", "Technology"),
    UniverseEntry("CA", "CA.PA", "CAC40", "Consumer Staples"),
    UniverseEntry("ACA", "ACA.PA", "CAC40", "Financials"),
    UniverseEntry("BN", "BN.PA", "CAC40", "Consumer Staples"),
    UniverseEntry("AM", "AM.PA", "CAC40", "Industrials"),
    UniverseEntry("DG", "DG.PA", "CAC40", "Industrials"),
    UniverseEntry("EDEN", "EDEN.PA", "CAC40", "Consumer Discretionary"),
    UniverseEntry("ENGI", "ENGI.PA", "CAC40", "Utilities"),
    UniverseEntry("EL", "EL.PA", "CAC40", "Consumer Staples"),
    UniverseEntry("ERF", "ERF.PA", "CAC40", "Consumer Discretionary"),
    UniverseEntry("RMS", "RMS.PA", "CAC40", "Consumer Discretionary"),
    UniverseEntry("KER", "KER.PA", "CAC40", "Consumer Discretionary"),
    UniverseEntry("LR", "LR.PA", "CAC40", "Industrials"),
    UniverseEntry("OR", "OR.PA", "CAC40", "Consumer Staples"),
    UniverseEntry("MC", "MC.PA", "CAC40", "Consumer Discretionary"),
    UniverseEntry("ML", "ML.PA", "CAC40", "Consumer Discretionary"),
    UniverseEntry("ORA", "ORA.PA", "CAC40", "Communication Services"),
    UniverseEntry("RI", "RI.PA", "CAC40", "Consumer Staples"),
    UniverseEntry("PUB", "PUB.PA", "CAC40", "Communication Services"),
    UniverseEntry("RNO", "RNO.PA", "CAC40", "Consumer Discretionary"),
    UniverseEntry("SAF", "SAF.PA", "CAC40", "Industrials"),
    UniverseEntry("SGO", "SGO.PA", "CAC40", "Industrials"),
    UniverseEntry("SAN", "SAN.PA", "CAC40", "Healthcare"),
    UniverseEntry("SU", "SU.PA", "CAC40", "Industrials"),
    UniverseEntry("GLE", "GLE.PA", "CAC40", "Financials"),
    UniverseEntry("STLAP", "STLAP.PA", "CAC40", "Consumer Discretionary"),
    UniverseEntry("STMPA", "STMPA.PA", "CAC40", "Technology"),
    UniverseEntry("TEP", "TEP.PA", "CAC40", "Communication Services"),
    UniverseEntry("HO", "HO.PA", "CAC40", "Industrials"),
    UniverseEntry("TTE", "TTE.PA", "CAC40", "Energy"),
    UniverseEntry("URW", "URW.PA", "CAC40", "Real Estate"),
    UniverseEntry("VIE", "VIE.PA", "CAC40", "Utilities"),
)


# ---- DAX 40 ----------------------------------------------------------

DAX40: Final[tuple[UniverseEntry, ...]] = (
    UniverseEntry("ADS", "ADS.XETRA", "DAX40", "Consumer Discretionary"),
    UniverseEntry("AIR", "AIR.XETRA", "DAX40", "Industrials"),
    UniverseEntry("ALV", "ALV.XETRA", "DAX40", "Financials"),
    UniverseEntry("BAS", "BAS.XETRA", "DAX40", "Materials"),
    UniverseEntry("BAYN", "BAYN.XETRA", "DAX40", "Healthcare"),
    UniverseEntry("BEI", "BEI.XETRA", "DAX40", "Consumer Staples"),
    UniverseEntry("BMW", "BMW.XETRA", "DAX40", "Consumer Discretionary"),
    UniverseEntry("BNR", "BNR.XETRA", "DAX40", "Technology"),
    UniverseEntry("CBK", "CBK.XETRA", "DAX40", "Financials"),
    UniverseEntry("CON", "CON.XETRA", "DAX40", "Consumer Discretionary"),
    UniverseEntry("1COV", "1COV.XETRA", "DAX40", "Materials"),
    UniverseEntry("DTG", "DTG.XETRA", "DAX40", "Industrials"),
    UniverseEntry("DBK", "DBK.XETRA", "DAX40", "Financials"),
    UniverseEntry("DB1", "DB1.XETRA", "DAX40", "Financials"),
    UniverseEntry("DHL", "DHL.XETRA", "DAX40", "Industrials"),
    UniverseEntry("DTE", "DTE.XETRA", "DAX40", "Communication Services"),
    UniverseEntry("EOAN", "EOAN.XETRA", "DAX40", "Utilities"),
    UniverseEntry("FRE", "FRE.XETRA", "DAX40", "Healthcare"),
    UniverseEntry("HNR1", "HNR1.XETRA", "DAX40", "Financials"),
    UniverseEntry("HEI", "HEI.XETRA", "DAX40", "Materials"),
    UniverseEntry("HEN3", "HEN3.XETRA", "DAX40", "Consumer Staples"),
    UniverseEntry("IFX", "IFX.XETRA", "DAX40", "Technology"),
    UniverseEntry("MBG", "MBG.XETRA", "DAX40", "Consumer Discretionary"),
    UniverseEntry("MRK", "MRK.XETRA", "DAX40", "Healthcare"),
    UniverseEntry("MTX", "MTX.XETRA", "DAX40", "Industrials"),
    UniverseEntry("MUV2", "MUV2.XETRA", "DAX40", "Financials"),
    UniverseEntry("PAH3", "PAH3.XETRA", "DAX40", "Consumer Discretionary"),
    UniverseEntry("P911", "P911.XETRA", "DAX40", "Consumer Discretionary"),
    UniverseEntry("QIA", "QIA.XETRA", "DAX40", "Healthcare"),
    UniverseEntry("RHM", "RHM.XETRA", "DAX40", "Industrials"),
    UniverseEntry("RWE", "RWE.XETRA", "DAX40", "Utilities"),
    UniverseEntry("SAP", "SAP.XETRA", "DAX40", "Technology"),
    UniverseEntry("SRT3", "SRT3.XETRA", "DAX40", "Healthcare"),
    UniverseEntry("SIE", "SIE.XETRA", "DAX40", "Industrials"),
    UniverseEntry("ENR", "ENR.XETRA", "DAX40", "Industrials"),
    UniverseEntry("SHL", "SHL.XETRA", "DAX40", "Healthcare"),
    UniverseEntry("SY1", "SY1.XETRA", "DAX40", "Technology"),
    UniverseEntry("VOW3", "VOW3.XETRA", "DAX40", "Consumer Discretionary"),
    UniverseEntry("VNA", "VNA.XETRA", "DAX40", "Real Estate"),
    UniverseEntry("ZAL", "ZAL.XETRA", "DAX40", "Consumer Discretionary"),
)


# ---- S&P 100 (representative subset of S&P 500) ---------------------

SP100: Final[tuple[UniverseEntry, ...]] = (
    UniverseEntry("AAPL", "AAPL.US", "SP100", "Technology"),
    UniverseEntry("ABBV", "ABBV.US", "SP100", "Healthcare"),
    UniverseEntry("ABT", "ABT.US", "SP100", "Healthcare"),
    UniverseEntry("ACN", "ACN.US", "SP100", "Technology"),
    UniverseEntry("ADBE", "ADBE.US", "SP100", "Technology"),
    UniverseEntry("AIG", "AIG.US", "SP100", "Financials"),
    UniverseEntry("AMD", "AMD.US", "SP100", "Technology"),
    UniverseEntry("AMGN", "AMGN.US", "SP100", "Healthcare"),
    UniverseEntry("AMT", "AMT.US", "SP100", "Real Estate"),
    UniverseEntry("AMZN", "AMZN.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("AVGO", "AVGO.US", "SP100", "Technology"),
    UniverseEntry("AXP", "AXP.US", "SP100", "Financials"),
    UniverseEntry("BA", "BA.US", "SP100", "Industrials"),
    UniverseEntry("BAC", "BAC.US", "SP100", "Financials"),
    UniverseEntry("BK", "BK.US", "SP100", "Financials"),
    UniverseEntry("BKNG", "BKNG.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("BLK", "BLK.US", "SP100", "Financials"),
    UniverseEntry("BMY", "BMY.US", "SP100", "Healthcare"),
    UniverseEntry("C", "C.US", "SP100", "Financials"),
    UniverseEntry("CAT", "CAT.US", "SP100", "Industrials"),
    UniverseEntry("CL", "CL.US", "SP100", "Consumer Staples"),
    UniverseEntry("CMCSA", "CMCSA.US", "SP100", "Communication Services"),
    UniverseEntry("COF", "COF.US", "SP100", "Financials"),
    UniverseEntry("COP", "COP.US", "SP100", "Energy"),
    UniverseEntry("COST", "COST.US", "SP100", "Consumer Staples"),
    UniverseEntry("CRM", "CRM.US", "SP100", "Technology"),
    UniverseEntry("CSCO", "CSCO.US", "SP100", "Technology"),
    UniverseEntry("CVS", "CVS.US", "SP100", "Healthcare"),
    UniverseEntry("CVX", "CVX.US", "SP100", "Energy"),
    UniverseEntry("DE", "DE.US", "SP100", "Industrials"),
    UniverseEntry("DIS", "DIS.US", "SP100", "Communication Services"),
    UniverseEntry("DOW", "DOW.US", "SP100", "Materials"),
    UniverseEntry("DUK", "DUK.US", "SP100", "Utilities"),
    UniverseEntry("EMR", "EMR.US", "SP100", "Industrials"),
    UniverseEntry("EXC", "EXC.US", "SP100", "Utilities"),
    UniverseEntry("F", "F.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("FDX", "FDX.US", "SP100", "Industrials"),
    UniverseEntry("GD", "GD.US", "SP100", "Industrials"),
    UniverseEntry("GE", "GE.US", "SP100", "Industrials"),
    UniverseEntry("GILD", "GILD.US", "SP100", "Healthcare"),
    UniverseEntry("GM", "GM.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("GOOG", "GOOG.US", "SP100", "Communication Services"),
    UniverseEntry("GOOGL", "GOOGL.US", "SP100", "Communication Services"),
    UniverseEntry("GS", "GS.US", "SP100", "Financials"),
    UniverseEntry("HD", "HD.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("HON", "HON.US", "SP100", "Industrials"),
    UniverseEntry("IBM", "IBM.US", "SP100", "Technology"),
    UniverseEntry("INTC", "INTC.US", "SP100", "Technology"),
    UniverseEntry("JNJ", "JNJ.US", "SP100", "Healthcare"),
    UniverseEntry("JPM", "JPM.US", "SP100", "Financials"),
    UniverseEntry("KO", "KO.US", "SP100", "Consumer Staples"),
    UniverseEntry("LIN", "LIN.US", "SP100", "Materials"),
    UniverseEntry("LLY", "LLY.US", "SP100", "Healthcare"),
    UniverseEntry("LMT", "LMT.US", "SP100", "Industrials"),
    UniverseEntry("LOW", "LOW.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("MA", "MA.US", "SP100", "Financials"),
    UniverseEntry("MCD", "MCD.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("MDT", "MDT.US", "SP100", "Healthcare"),
    UniverseEntry("MET", "MET.US", "SP100", "Financials"),
    UniverseEntry("META", "META.US", "SP100", "Communication Services"),
    UniverseEntry("MMM", "MMM.US", "SP100", "Industrials"),
    UniverseEntry("MO", "MO.US", "SP100", "Consumer Staples"),
    UniverseEntry("MRK", "MRK.US", "SP100", "Healthcare"),
    UniverseEntry("MS", "MS.US", "SP100", "Financials"),
    UniverseEntry("MSFT", "MSFT.US", "SP100", "Technology"),
    UniverseEntry("NEE", "NEE.US", "SP100", "Utilities"),
    UniverseEntry("NFLX", "NFLX.US", "SP100", "Communication Services"),
    UniverseEntry("NKE", "NKE.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("NVDA", "NVDA.US", "SP100", "Technology"),
    UniverseEntry("ORCL", "ORCL.US", "SP100", "Technology"),
    UniverseEntry("PEP", "PEP.US", "SP100", "Consumer Staples"),
    UniverseEntry("PFE", "PFE.US", "SP100", "Healthcare"),
    UniverseEntry("PG", "PG.US", "SP100", "Consumer Staples"),
    UniverseEntry("PM", "PM.US", "SP100", "Consumer Staples"),
    UniverseEntry("PYPL", "PYPL.US", "SP100", "Financials"),
    UniverseEntry("QCOM", "QCOM.US", "SP100", "Technology"),
    UniverseEntry("RTX", "RTX.US", "SP100", "Industrials"),
    UniverseEntry("SBUX", "SBUX.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("SCHW", "SCHW.US", "SP100", "Financials"),
    UniverseEntry("SO", "SO.US", "SP100", "Utilities"),
    UniverseEntry("SPG", "SPG.US", "SP100", "Real Estate"),
    UniverseEntry("T", "T.US", "SP100", "Communication Services"),
    UniverseEntry("TGT", "TGT.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("TMO", "TMO.US", "SP100", "Healthcare"),
    UniverseEntry("TSLA", "TSLA.US", "SP100", "Consumer Discretionary"),
    UniverseEntry("TXN", "TXN.US", "SP100", "Technology"),
    UniverseEntry("UNH", "UNH.US", "SP100", "Healthcare"),
    UniverseEntry("UNP", "UNP.US", "SP100", "Industrials"),
    UniverseEntry("UPS", "UPS.US", "SP100", "Industrials"),
    UniverseEntry("USB", "USB.US", "SP100", "Financials"),
    UniverseEntry("V", "V.US", "SP100", "Financials"),
    UniverseEntry("VZ", "VZ.US", "SP100", "Communication Services"),
    UniverseEntry("WBA", "WBA.US", "SP100", "Consumer Staples"),
    UniverseEntry("WFC", "WFC.US", "SP100", "Financials"),
    UniverseEntry("WMT", "WMT.US", "SP100", "Consumer Staples"),
    UniverseEntry("XOM", "XOM.US", "SP100", "Energy"),
    UniverseEntry("ADP", "ADP.US", "SP100", "Industrials"),
    UniverseEntry("BKR", "BKR.US", "SP100", "Energy"),
    UniverseEntry("KHC", "KHC.US", "SP100", "Consumer Staples"),
    UniverseEntry("KMI", "KMI.US", "SP100", "Energy"),
    UniverseEntry("MDLZ", "MDLZ.US", "SP100", "Consumer Staples"),
)


# ---- NASDAQ 100 (additional tech-heavy names not already in SP100) --
# Only entries that don't overlap with SP100 to avoid duplicate scans.

NASDAQ100_EXTRA: Final[tuple[UniverseEntry, ...]] = (
    UniverseEntry("ADI", "ADI.US", "NASDAQ100", "Technology"),
    UniverseEntry("ADSK", "ADSK.US", "NASDAQ100", "Technology"),
    UniverseEntry("AEP", "AEP.US", "NASDAQ100", "Utilities"),
    UniverseEntry("ALGN", "ALGN.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("AMAT", "AMAT.US", "NASDAQ100", "Technology"),
    UniverseEntry("ANSS", "ANSS.US", "NASDAQ100", "Technology"),
    UniverseEntry("ASML", "ASML.US", "NASDAQ100", "Technology"),
    UniverseEntry("AZN", "AZN.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("BIIB", "BIIB.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("CDNS", "CDNS.US", "NASDAQ100", "Technology"),
    UniverseEntry("CDW", "CDW.US", "NASDAQ100", "Technology"),
    UniverseEntry("CEG", "CEG.US", "NASDAQ100", "Utilities"),
    UniverseEntry("CHTR", "CHTR.US", "NASDAQ100", "Communication Services"),
    UniverseEntry("CPRT", "CPRT.US", "NASDAQ100", "Industrials"),
    UniverseEntry("CRWD", "CRWD.US", "NASDAQ100", "Technology"),
    UniverseEntry("CSGP", "CSGP.US", "NASDAQ100", "Real Estate"),
    UniverseEntry("CSX", "CSX.US", "NASDAQ100", "Industrials"),
    UniverseEntry("CTAS", "CTAS.US", "NASDAQ100", "Industrials"),
    UniverseEntry("CTSH", "CTSH.US", "NASDAQ100", "Technology"),
    UniverseEntry("DDOG", "DDOG.US", "NASDAQ100", "Technology"),
    UniverseEntry("DLTR", "DLTR.US", "NASDAQ100", "Consumer Staples"),
    UniverseEntry("DXCM", "DXCM.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("EA", "EA.US", "NASDAQ100", "Communication Services"),
    UniverseEntry("ENPH", "ENPH.US", "NASDAQ100", "Technology"),
    UniverseEntry("EXC", "EXC.US", "NASDAQ100", "Utilities"),
    UniverseEntry("FANG", "FANG.US", "NASDAQ100", "Energy"),
    UniverseEntry("FAST", "FAST.US", "NASDAQ100", "Industrials"),
    UniverseEntry("FTNT", "FTNT.US", "NASDAQ100", "Technology"),
    UniverseEntry("GEHC", "GEHC.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("GFS", "GFS.US", "NASDAQ100", "Technology"),
    UniverseEntry("HON", "HON.US", "NASDAQ100", "Industrials"),
    UniverseEntry("IDXX", "IDXX.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("ILMN", "ILMN.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("INTU", "INTU.US", "NASDAQ100", "Technology"),
    UniverseEntry("ISRG", "ISRG.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("KDP", "KDP.US", "NASDAQ100", "Consumer Staples"),
    UniverseEntry("KLAC", "KLAC.US", "NASDAQ100", "Technology"),
    UniverseEntry("LRCX", "LRCX.US", "NASDAQ100", "Technology"),
    UniverseEntry("LULU", "LULU.US", "NASDAQ100", "Consumer Discretionary"),
    UniverseEntry("MAR", "MAR.US", "NASDAQ100", "Consumer Discretionary"),
    UniverseEntry("MCHP", "MCHP.US", "NASDAQ100", "Technology"),
    UniverseEntry("MDB", "MDB.US", "NASDAQ100", "Technology"),
    UniverseEntry("MELI", "MELI.US", "NASDAQ100", "Consumer Discretionary"),
    UniverseEntry("MNST", "MNST.US", "NASDAQ100", "Consumer Staples"),
    UniverseEntry("MRNA", "MRNA.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("MU", "MU.US", "NASDAQ100", "Technology"),
    UniverseEntry("NXPI", "NXPI.US", "NASDAQ100", "Technology"),
    UniverseEntry("ODFL", "ODFL.US", "NASDAQ100", "Industrials"),
    UniverseEntry("ON", "ON.US", "NASDAQ100", "Technology"),
    UniverseEntry("PANW", "PANW.US", "NASDAQ100", "Technology"),
    UniverseEntry("PAYX", "PAYX.US", "NASDAQ100", "Industrials"),
    UniverseEntry("PCAR", "PCAR.US", "NASDAQ100", "Industrials"),
    UniverseEntry("PDD", "PDD.US", "NASDAQ100", "Consumer Discretionary"),
    UniverseEntry("REGN", "REGN.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("ROP", "ROP.US", "NASDAQ100", "Industrials"),
    UniverseEntry("ROST", "ROST.US", "NASDAQ100", "Consumer Discretionary"),
    UniverseEntry("SIRI", "SIRI.US", "NASDAQ100", "Communication Services"),
    UniverseEntry("SNPS", "SNPS.US", "NASDAQ100", "Technology"),
    UniverseEntry("TEAM", "TEAM.US", "NASDAQ100", "Technology"),
    UniverseEntry("TMUS", "TMUS.US", "NASDAQ100", "Communication Services"),
    UniverseEntry("TTD", "TTD.US", "NASDAQ100", "Technology"),
    UniverseEntry("TTWO", "TTWO.US", "NASDAQ100", "Communication Services"),
    UniverseEntry("VRSK", "VRSK.US", "NASDAQ100", "Industrials"),
    UniverseEntry("VRTX", "VRTX.US", "NASDAQ100", "Healthcare"),
    UniverseEntry("WBD", "WBD.US", "NASDAQ100", "Communication Services"),
    UniverseEntry("WDAY", "WDAY.US", "NASDAQ100", "Technology"),
    UniverseEntry("XEL", "XEL.US", "NASDAQ100", "Utilities"),
    UniverseEntry("ZS", "ZS.US", "NASDAQ100", "Technology"),
)


# ---- V1.1 §22.4 EU600 additions --------------------------------------
#
# Representative top-cap additions across the major EU indices outside
# the V1 Bel/AEX/CAC/DAX set so the morning chain can offer a broader
# EU cross-section. Not the full Stoxx 600 (that would balloon this
# module); production deployments resolve the full Stoxx 600 from the
# EODHD index-constituents bulk endpoint — a post-V1.1 widening.

EU600_EXTRA: Final[tuple[UniverseEntry, ...]] = (
    # UK FTSE 100 — top names
    UniverseEntry("AZN", "AZN.LSE", "FTSE100", "Healthcare", "GB"),
    UniverseEntry("BARC", "BARC.LSE", "FTSE100", "Financials", "GB"),
    UniverseEntry("BP", "BP.LSE", "FTSE100", "Energy", "GB"),
    UniverseEntry("DGE", "DGE.LSE", "FTSE100", "Consumer Staples", "GB"),
    UniverseEntry("GSK", "GSK.LSE", "FTSE100", "Healthcare", "GB"),
    UniverseEntry("HSBA", "HSBA.LSE", "FTSE100", "Financials", "GB"),
    UniverseEntry("LLOY", "LLOY.LSE", "FTSE100", "Financials", "GB"),
    UniverseEntry("RIO", "RIO.LSE", "FTSE100", "Materials", "GB"),
    UniverseEntry("SHEL", "SHEL.LSE", "FTSE100", "Energy", "GB"),
    UniverseEntry("ULVR", "ULVR.LSE", "FTSE100", "Consumer Staples", "GB"),
    UniverseEntry("VOD", "VOD.LSE", "FTSE100", "Communication Services", "GB"),
    # Swiss SLI — top names
    UniverseEntry("NESN", "NESN.SW", "SLI", "Consumer Staples", "CH"),
    UniverseEntry("ROG", "ROG.SW", "SLI", "Healthcare", "CH"),
    UniverseEntry("NOVN", "NOVN.SW", "SLI", "Healthcare", "CH"),
    UniverseEntry("UBSG", "UBSG.SW", "SLI", "Financials", "CH"),
    UniverseEntry("ZURN", "ZURN.SW", "SLI", "Financials", "CH"),
    UniverseEntry("ABBN", "ABBN.SW", "SLI", "Industrials", "CH"),
    UniverseEntry("SREN", "SREN.SW", "SLI", "Financials", "CH"),
    # IBEX 35 — top names
    UniverseEntry("ITX", "ITX.MC", "IBEX35", "Consumer Discretionary", "ES"),
    UniverseEntry("SAN", "SAN.MC", "IBEX35", "Financials", "ES"),
    UniverseEntry("IBE", "IBE.MC", "IBEX35", "Utilities", "ES"),
    UniverseEntry("TEF", "TEF.MC", "IBEX35", "Communication Services", "ES"),
    UniverseEntry("BBVA", "BBVA.MC", "IBEX35", "Financials", "ES"),
    UniverseEntry("REP", "REP.MC", "IBEX35", "Energy", "ES"),
    # FTSE MIB — top names
    UniverseEntry("ENI", "ENI.MI", "FTSEMIB", "Energy", "IT"),
    UniverseEntry("ISP", "ISP.MI", "FTSEMIB", "Financials", "IT"),
    UniverseEntry("UCG", "UCG.MI", "FTSEMIB", "Financials", "IT"),
    UniverseEntry("STLAM", "STLAM.MI", "FTSEMIB", "Consumer Discretionary", "IT"),
    UniverseEntry("ENEL", "ENEL.MI", "FTSEMIB", "Utilities", "IT"),
    UniverseEntry("RACE", "RACE.MI", "FTSEMIB", "Consumer Discretionary", "IT"),
    UniverseEntry("G", "G.MI", "FTSEMIB", "Financials", "IT"),
    # Stoxx Nordic 30 — top names
    UniverseEntry("NOVO-B", "NOVO-B.CO", "NORDIC30", "Healthcare", "DK"),
    UniverseEntry("MAERSK-B", "MAERSK-B.CO", "NORDIC30", "Industrials", "DK"),
    UniverseEntry("ATCO-A", "ATCO-A.ST", "NORDIC30", "Industrials", "SE"),
    UniverseEntry("VOLV-B", "VOLV-B.ST", "NORDIC30", "Industrials", "SE"),
    UniverseEntry("ERIC-B", "ERIC-B.ST", "NORDIC30", "Communication Services", "SE"),
    UniverseEntry("EQNR", "EQNR.OL", "NORDIC30", "Energy", "NO"),
    UniverseEntry("NHY", "NHY.OL", "NORDIC30", "Materials", "NO"),
)


# ---- V1.1 §22.4 ALL_5K representative additions ---------------------
#
# A small US small/mid-cap sample so the locked operator surface
# exists from Slice 31. Production deployments resolve the full
# ~5 000-ticker universe from the EODHD bulk-list endpoints (a
# post-V1.1 widening).

ALL_5K_EXTRA: Final[tuple[UniverseEntry, ...]] = (
    UniverseEntry("PLTR", "PLTR.US", "RUSSELL1000", "Technology", "US"),
    UniverseEntry("ROKU", "ROKU.US", "RUSSELL1000", "Communication Services", "US"),
    UniverseEntry("ETSY", "ETSY.US", "RUSSELL1000", "Consumer Discretionary", "US"),
    UniverseEntry("ZM", "ZM.US", "RUSSELL1000", "Communication Services", "US"),
    UniverseEntry("DOCU", "DOCU.US", "RUSSELL1000", "Technology", "US"),
    UniverseEntry("DKNG", "DKNG.US", "RUSSELL1000", "Consumer Discretionary", "US"),
    UniverseEntry("UPST", "UPST.US", "RUSSELL2000", "Financials", "US"),
    UniverseEntry("AFRM", "AFRM.US", "RUSSELL2000", "Financials", "US"),
    UniverseEntry("RBLX", "RBLX.US", "RUSSELL1000", "Communication Services", "US"),
    UniverseEntry("U", "U.US", "RUSSELL1000", "Technology", "US"),
)


_STARTER_50_SET: tuple[UniverseEntry, ...] = (
    *BEL20,
    *AEX,
)

_SP500_SET: tuple[UniverseEntry, ...] = (
    *BEL20,
    *AEX,
    *CAC40,
    *DAX40,
    *SP100,
    *NASDAQ100_EXTRA,
)

_EU600_SET: tuple[UniverseEntry, ...] = (
    *_SP500_SET,
    *EU600_EXTRA,
)

_ALL_5K_SET: tuple[UniverseEntry, ...] = (
    *_EU600_SET,
    *ALL_5K_EXTRA,
)

_LOCKED_UNIVERSE_BY_SET: dict[str, tuple[UniverseEntry, ...]] = {
    UNIVERSE_SET_STARTER_50: _STARTER_50_SET,
    UNIVERSE_SET_SP500: _SP500_SET,
    UNIVERSE_SET_EU600: _EU600_SET,
    UNIVERSE_SET_ALL_5K: _ALL_5K_SET,
}


# ---- Per-index multi-select (operator-pickable markets) -----------------
#
# The locked sets above bundle indices into all-or-nothing groups. The
# operator may instead pick any subset of indices via the new
# ``universe_scan_index_codes`` setting (a comma-separated list of these
# codes). ``compose_universe_from_index_codes`` builds the deduped union.

INDEX_CODE_BEL20: Final[str] = "BEL20"
INDEX_CODE_AEX: Final[str] = "AEX"
INDEX_CODE_CAC40: Final[str] = "CAC40"
INDEX_CODE_DAX40: Final[str] = "DAX40"
INDEX_CODE_FTSE100: Final[str] = "FTSE100"
INDEX_CODE_FTSEMIB: Final[str] = "FTSEMIB"
INDEX_CODE_IBEX35: Final[str] = "IBEX35"
INDEX_CODE_NORDIC30: Final[str] = "NORDIC30"
INDEX_CODE_SLI: Final[str] = "SLI"
INDEX_CODE_SP100: Final[str] = "SP100"
INDEX_CODE_NASDAQ100: Final[str] = "NASDAQ100"
INDEX_CODE_RUSSELL1000: Final[str] = "RUSSELL1000"
INDEX_CODE_RUSSELL2000: Final[str] = "RUSSELL2000"

# Locked set of pickable index codes. Adding a new index here is the
# *only* place that has to change — ``compose_universe_from_index_codes``
# discovers entries by scanning every locked set with this code.
LOCKED_INDEX_CODES: Final[frozenset[str]] = frozenset(
    {
        INDEX_CODE_BEL20,
        INDEX_CODE_AEX,
        INDEX_CODE_CAC40,
        INDEX_CODE_DAX40,
        INDEX_CODE_FTSE100,
        INDEX_CODE_FTSEMIB,
        INDEX_CODE_IBEX35,
        INDEX_CODE_NORDIC30,
        INDEX_CODE_SLI,
        INDEX_CODE_SP100,
        INDEX_CODE_NASDAQ100,
        INDEX_CODE_RUSSELL1000,
        INDEX_CODE_RUSSELL2000,
    }
)


# Human-readable labels per index code. The UI multi-select uses these.
INDEX_CODE_LABELS_NL: Final[dict[str, str]] = {
    INDEX_CODE_BEL20: "België — Bel20",
    INDEX_CODE_AEX: "Nederland — AEX",
    INDEX_CODE_CAC40: "Frankrijk — CAC 40",
    INDEX_CODE_DAX40: "Duitsland — DAX 40",
    INDEX_CODE_FTSE100: "Verenigd Koninkrijk — FTSE 100",
    INDEX_CODE_FTSEMIB: "Italië — FTSE MIB",
    INDEX_CODE_IBEX35: "Spanje — IBEX 35",
    INDEX_CODE_NORDIC30: "Noord-Europa — Nordic 30",
    INDEX_CODE_SLI: "Zwitserland — SLI",
    INDEX_CODE_SP100: "VS — S&P 100",
    INDEX_CODE_NASDAQ100: "VS — NASDAQ 100",
    INDEX_CODE_RUSSELL1000: "VS — Russell 1000 (extras)",
    INDEX_CODE_RUSSELL2000: "VS — Russell 2000 (extras)",
}


def parse_index_codes(raw: str) -> tuple[str, ...]:
    """Parse a comma-separated index-code list and reject unknown codes.

    Leading/trailing whitespace is stripped per token. Empty tokens are
    silently dropped. The result preserves operator-supplied order and
    deduplicates.
    """

    seen: set[str] = set()
    out: list[str] = []
    for raw_token in (raw or "").split(","):
        token = raw_token.strip()
        if not token:
            continue
        if token not in LOCKED_INDEX_CODES:
            raise ValueError(
                f"unknown universe_scan_index_code {token!r}; "
                f"must be one of {sorted(LOCKED_INDEX_CODES)}"
            )
        if token in seen:
            continue
        seen.add(token)
        out.append(token)
    return tuple(out)


def compose_universe_from_index_codes(
    codes: Sequence[str],
) -> tuple[UniverseEntry, ...]:
    """Build the deduplicated universe entry tuple for a multi-select.

    Scans the broadest locked set (``ALL_5K``) and keeps every entry whose
    ``index_code`` is in ``codes``. Order in the result follows the
    operator-supplied ``codes`` order — within each index the registry's
    own order is preserved.
    """

    if not codes:
        return ()
    requested = list(codes)
    by_code: dict[str, list[UniverseEntry]] = {code: [] for code in requested}
    for entry in _ALL_5K_SET:
        if entry.index_code in by_code:
            by_code[entry.index_code].append(entry)
    flat: list[UniverseEntry] = []
    for code in requested:
        flat.extend(by_code[code])
    return _dedupe_by_eodhd_symbol(flat)


def _dedupe_by_eodhd_symbol(
    entries: Sequence[UniverseEntry],
) -> tuple[UniverseEntry, ...]:
    seen: set[str] = set()
    deduped: list[UniverseEntry] = []
    for entry in entries:
        if entry.eodhd_symbol in seen:
            continue
        seen.add(entry.eodhd_symbol)
        deduped.append(entry)
    return tuple(deduped)


def locked_universe(
    set_code: str = DEFAULT_UNIVERSE_SET,
) -> tuple[UniverseEntry, ...]:
    """Return the deduplicated locked universe for the requested set.

    V1.1 §22.4: ``set_code`` must be one of
    :data:`LOCKED_UNIVERSE_SETS` (``SP500`` / ``EU600`` / ``ALL_5K``);
    unknown codes raise ``ValueError`` so a typo in the operator's
    env doesn't silently fall back to a smaller / larger set.

    De-duplication is by ``eodhd_symbol`` — when the same ticker
    appears in multiple indices we keep the first occurrence so the
    scan never hits EODHD twice for the same symbol.
    """

    if set_code not in LOCKED_UNIVERSE_SETS:
        raise ValueError(
            f"universe_set must be one of {sorted(LOCKED_UNIVERSE_SETS)}, "
            f"got {set_code!r}"
        )
    return _dedupe_by_eodhd_symbol(_LOCKED_UNIVERSE_BY_SET[set_code])


def universe_by_index(
    index_code: str,
    *,
    set_code: str = DEFAULT_UNIVERSE_SET,
) -> Sequence[UniverseEntry]:
    return tuple(
        e for e in locked_universe(set_code) if e.index_code == index_code
    )


__all__ = [
    "AEX",
    "ALL_5K_EXTRA",
    "BEL20",
    "CAC40",
    "DAX40",
    "DEFAULT_UNIVERSE_SET",
    "EU600_EXTRA",
    "LOCKED_UNIVERSE_SETS",
    "NASDAQ100_EXTRA",
    "SP100",
    "UNIVERSE_SET_ALL_5K",
    "UNIVERSE_SET_EU600",
    "UNIVERSE_SET_SP500",
    "UniverseEntry",
    "locked_universe",
    "universe_by_index",
]
