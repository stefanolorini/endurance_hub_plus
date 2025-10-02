import zipfile, xml.etree.ElementTree as ET, io, pandas as pd

CODES = {
  "HRV": "HKQuantityTypeIdentifierHeartRateVariabilitySDNN",
  "RHR": "HKQuantityTypeIdentifierRestingHeartRate",
  "WEIGHT": "HKQuantityTypeIdentifierBodyMass",
  "BODY_FAT": "HKQuantityTypeIdentifierBodyFatPercentage"
}

def parse_health_export(zip_bytes: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        with z.open("apple_health_export/export.xml") as f:
            tree = ET.parse(f)
    root = tree.getroot()
    recs = []
    for r in root.findall("Record"):
        t = r.get("type")
        start = r.get("startDate")
        value = r.get("value")
        if t in CODES.values():
            recs.append({"type": t, "date": start[:10], "value": float(value) if value else None})
    df = pd.DataFrame(recs)
    if df.empty:
        return df
    daily = df.pivot_table(index="date", columns="type", values="value", aggfunc="mean").reset_index()
    daily = daily.rename(columns={
        CODES["HRV"]:"hrv_ms",
        CODES["RHR"]:"rhr",
        CODES["WEIGHT"]:"weight_kg",
        CODES["BODY_FAT"]:"body_fat_pct"
    })
    return daily
