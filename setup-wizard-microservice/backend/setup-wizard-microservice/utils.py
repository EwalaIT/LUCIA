from models import Zone

# ---------------------------------------------------------
# Constantes y utilidades para días
# ---------------------------------------------------------
DAY_ORDER = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

DAY_LABELS_EN = {
    "monday": "Monday",
    "tuesday": "Tuesday",
    "wednesday": "Wednesday",
    "thursday": "Thursday",
    "friday": "Friday",
    "saturday": "Saturday",
    "sunday": "Sunday",
}

def parse_days_field(days_field):
    """
    Acepta:
      - "monday"
      - "monday,tuesday"
      - "monday, wednesday"
    Devuelve set() con días en minúsculas.
    """
    if not days_field:
        return set()
    if isinstance(days_field, (list, tuple, set)):
        items = days_field
    else:
        items = [p.strip().lower() for p in str(days_field).split(",") if p.strip()]
    return set([d for d in items if d in DAY_ORDER])

def humanize_days(days_set):
    """
    Convierte un set {'monday','tuesday',...} en texto natural.
    Ejemplos:
      {'monday','tuesday','wednesday','thursday','friday'} -> "Monday to Friday"
      {'monday','wednesday'} -> "Monday and Wednesday"
      {'tuesday'} -> "Tuesday"
    """
    if not days_set:
        return ""

    # ordenar según DAY_ORDER
    ordered_days = [d for d in DAY_ORDER if d in days_set]
    if not ordered_days:
        return ""

    # convertir a índices y detectar rangos consecutivos
    idxs = [DAY_ORDER.index(d) for d in ordered_days]

    ranges = []
    start_idx = prev_idx = idxs[0]
    for i in idxs[1:]:
        if i == prev_idx + 1:
            prev_idx = i
            continue
        else:
            ranges.append((start_idx, prev_idx))
            start_idx = prev_idx = i
    ranges.append((start_idx, prev_idx))

    # Si un único rango y cubre al menos 2 días consecutivos => "A to B"
    if len(ranges) == 1:
        a_idx, b_idx = ranges[0]
        if a_idx != b_idx:
            a_day = DAY_LABELS_EN[DAY_ORDER[a_idx]]
            b_day = DAY_LABELS_EN[DAY_ORDER[b_idx]]
            return f"{a_day} to {b_day}"

    # Sino, listarlo con comas y 'and'
    readable = [DAY_LABELS_EN[d] for d in ordered_days]
    if len(readable) == 1:
        return readable[0]
    if len(readable) == 2:
        return f"{readable[0]} and {readable[1]}"
    return ", ".join(readable[:-1]) + f" and {readable[-1]}"

# ---------------------------------------------------------
# Función auxiliar: generar reglas en lenguaje natural
# ---------------------------------------------------------
def generate_natural_language_rules(schedules_list, db_session):
    """
    schedules_list: lista de instancias de SetupSchedule (pueden ser objetos ORM que aún no están commitados)
    db_session: sesión SQLAlchemy
    Retorna: lista de dicts: [{"rule_text": "..."}]
    """
    # 1) resolver zone_id -> zone.name
    zone_ids = {int(s.zone_id) for s in schedules_list if getattr(s, "zone_id", None) is not None}
    zone_map = {}
    if zone_ids:
        zones = db_session.query(Zone).filter(Zone.id.in_(zone_ids)).all()
        zone_map = {z.id: z.name for z in zones}

    # 2) Agrupar por clave estructural
    # clave: (zone_id, start_time, end_time, temp_min, temp_max) -> set(days)
    groups = {}
    for s in schedules_list:
        # s.days puede contener "monday" o "monday,tuesday" -> lo parseamos
        days_in_entry = parse_days_field(getattr(s, "days", "") or "")

        key = (
            int(getattr(s, "zone_id", 0)),
            getattr(s, "start_time"),
            getattr(s, "end_time"),
            float(getattr(s, "temp_min", 0.0) or 0.0),
            float(getattr(s, "temp_max", 0.0) or 0.0),
        )
        if key not in groups:
            groups[key] = set()
        groups[key].update(days_in_entry)

    # 3) Construir textos naturales
    results = []
    for (zone_id, start_time, end_time, tmin, tmax), days_set in groups.items():
        # Si no hay días parseables, ignorar
        if not days_set:
            continue

        zone_name = zone_map.get(zone_id, f"Zone {zone_id}")

        day_text = humanize_days(days_set)

        # start_time/end_time pueden ser objetos time o strings
        def fmt_time(v):
            if v is None:
                return ""
            if isinstance(v, str):
                # asume "HH:MM"
                return v
            try:
                return v.strftime("%H:%M")
            except Exception:
                return str(v)

        start_str = fmt_time(start_time)
        end_str = fmt_time(end_time)

        # Formato final (profesional, en inglés según requisito)
        rule_text = (
            f"In zone {zone_name}, on {day_text} between {start_str} and {end_str}, "
            f"maintain temperature between {int(round(tmin))}°C and {int(round(tmax))}°C."
        )

        results.append({"rule_text": rule_text})

    return results