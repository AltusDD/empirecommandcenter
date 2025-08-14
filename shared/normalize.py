# shared/normalize.py
# Global label reconciliation so every endpoint returns canonical keys.
# Safe to drop-in; does not remove original keys, only adds canonical ones.

from typing import List, Dict, Any, Optional

def _coalesce(*vals):
    for v in vals:
        if v is not None and v != "":
            return v
    return None

def normalize_items(resource: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add canonical keys to every row coming from Supabase views so the frontend
    can rely on one schema regardless of source column names.

    Canonical keys produced:
      PROPERTIES:
        property_id, property_name, address1, city, state,
        total_units, occupied_units, occupancy_rate
      UNITS:
        unit_id, unit_name, property_id, property_name, address1, city, state, status
      LEASES:
        lease_id, start_date, end_date, rent_cents, lease_status,
        property_id, property_name, unit_id, unit_name, tenant_name
      TENANTS:
        tenant_name, property_id, property_name, unit_id, unit_name,
        start_date, end_date, lease_status, city, state
      OWNERS:
        owner_name, properties_count, units_count, occupied_units, occupancy_rate
    """
    if not isinstance(items, list):
        return items

    canon = []
    r = (resource or "").lower()

    for row in items:
        if not isinstance(row, dict):
            canon.append(row)
            continue

        out = dict(row)  # keep original keys too

        if r == "properties":
            out["property_id"]    = _coalesce(row.get("property_id"), row.get("id"))
            out["property_name"]  = _coalesce(row.get("property_name"), row.get("name"),
                                              row.get("address1"), row.get("address_street1"))
            out["address1"]       = _coalesce(row.get("address1"), row.get("address_street1"))
            out["city"]           = row.get("city")
            out["state"]          = row.get("state")
            out["total_units"]    = _coalesce(row.get("total_units"), row.get("units"), 0)
            out["occupied_units"] = _coalesce(row.get("occupied_units"), row.get("occupied"), 0)
            if out.get("occupancy_rate") is None:
                tu = out.get("total_units") or 0
                ou = out.get("occupied_units") or 0
                out["occupancy_rate"] = (ou / tu) if tu else 0.0

        elif r == "units":
            out["unit_id"]        = _coalesce(row.get("unit_id"), row.get("id"))
            out["unit_name"]      = _coalesce(row.get("unit_name"), row.get("unit_number"), "-")
            out["status"]         = row.get("status")
            out["property_id"]    = _coalesce(row.get("property_id"), row.get("pid"))
            out["address1"]       = _coalesce(row.get("address1"), row.get("address_street1"))
            out["city"]           = row.get("city")
            out["state"]          = row.get("state")
            out["property_name"]  = _coalesce(
                row.get("property_name"),
                row.get("address1"),
                row.get("address_street1"),
                ("Property %s" % out["property_id"]) if out.get("property_id") else "Unknown Property"
            )

        elif r == "leases":
            out["lease_id"]       = _coalesce(row.get("lease_id"), row.get("id"))
            out["start_date"]     = _coalesce(row.get("start_date"), row.get("lease_start"))
            out["end_date"]       = _coalesce(row.get("end_date"), row.get("lease_end"))
            out["rent_cents"]     = _coalesce(row.get("rent_cents"), row.get("rent"))
            out["lease_status"]   = _coalesce(row.get("lease_status"), row.get("status"))
            out["unit_id"]        = _coalesce(row.get("unit_id"), row.get("uid"))
            out["unit_name"]      = _coalesce(row.get("unit_name"), row.get("unit_number"))
            out["property_id"]    = _coalesce(row.get("property_id"), row.get("pid"))
            out["property_name"]  = _coalesce(row.get("property_name"), row.get("address1"), row.get("address_street1"))
            out["tenant_name"]    = _coalesce(row.get("tenant_name"), row.get("tenant"))

        elif r == "tenants":
            out["tenant_name"]    = _coalesce(row.get("tenant_name"), row.get("name"))
            out["start_date"]     = _coalesce(row.get("start_date"), row.get("lease_start"))
            out["end_date"]       = _coalesce(row.get("end_date"), row.get("lease_end"))
            out["lease_status"]   = _coalesce(row.get("lease_status"), row.get("status"))
            out["unit_id"]        = _coalesce(row.get("unit_id"), row.get("uid"))
            out["unit_name"]      = _coalesce(row.get("unit_name"), row.get("unit_number"))
            out["property_id"]    = _coalesce(row.get("property_id"), row.get("pid"))
            out["property_name"]  = _coalesce(row.get("property_name"), row.get("address1"), row.get("address_street1"))
            out["city"]           = row.get("city")
            out["state"]          = row.get("state")

        elif r == "owners":
            out["owner_name"]      = _coalesce(row.get("owner_name"), row.get("name"), row.get("display_name"), row.get("full_name"))
            out["properties_count"]= _coalesce(row.get("properties_count"), row.get("properties"), 0)
            out["units_count"]     = _coalesce(row.get("units_count"), row.get("units"), 0)
            out["occupied_units"]  = _coalesce(row.get("occupied_units"), 0)
            if out.get("occupancy_rate") is None:
                tu = out.get("units_count") or 0
                ou = out.get("occupied_units") or 0
                out["occupancy_rate"] = (ou / tu) if tu else 0.0

        canon.append(out)

    return canon
