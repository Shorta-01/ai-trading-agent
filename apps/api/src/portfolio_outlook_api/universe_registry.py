"""V1 universe registry — locked in `version-1-product-experience-locks.md §21.6`.

Static Python tables listing the tickers the daily scan iterates over.
Each entry carries:

* ``symbol`` — the exchange-local ticker (e.g. ``"ASML"``, ``"AAPL"``)
* ``eodhd_symbol`` — the EODHD-formatted symbol (``"ASML.AS"``,
  ``"AAPL.US"``) used by the fundamentals + bars endpoints
* ``index_code`` — the index the ticker belongs to (e.g. ``"BEL20"``)
* ``sector`` — best-effort sector hint for the QVM cross-section;
  EODHD's `Sector` field overrides this when available

This module is pure Python; it does no I/O. The full ~5 000-ticker
universe will be expanded in a later slice. For Slice 17 we ship a
representative set covering the locked indices:

* Bel20 (Belgian large-cap)
* AEX 25 (Dutch large-cap)
* CAC 40 (French large-cap)
* DAX 40 (German large-cap)
* S&P 100 (US large-cap, representative subset of S&P 500)
* NASDAQ 100 (US tech-heavy large-cap)

Roughly 325 tickers — large enough to make the QVM cross-section
meaningful, small enough to fit in one Python module and finish a
scan well under EODHD's daily quota.
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


_LOCKED_UNIVERSE: tuple[UniverseEntry, ...] = (
    *BEL20,
    *AEX,
    *CAC40,
    *DAX40,
    *SP100,
    *NASDAQ100_EXTRA,
)


def locked_universe() -> tuple[UniverseEntry, ...]:
    """Return the full V1 locked universe.

    De-duplication is by ``eodhd_symbol`` — when the same ticker appears
    in multiple indices (e.g. ``HON.US`` is in both S&P 100 and NASDAQ
    100) we keep the first occurrence so the scan never hits EODHD
    twice for the same symbol.
    """

    seen: set[str] = set()
    deduped: list[UniverseEntry] = []
    for entry in _LOCKED_UNIVERSE:
        if entry.eodhd_symbol in seen:
            continue
        seen.add(entry.eodhd_symbol)
        deduped.append(entry)
    return tuple(deduped)


def universe_by_index(index_code: str) -> Sequence[UniverseEntry]:
    return tuple(e for e in locked_universe() if e.index_code == index_code)


__all__ = [
    "UniverseEntry",
    "BEL20",
    "AEX",
    "CAC40",
    "DAX40",
    "SP100",
    "NASDAQ100_EXTRA",
    "locked_universe",
    "universe_by_index",
]
