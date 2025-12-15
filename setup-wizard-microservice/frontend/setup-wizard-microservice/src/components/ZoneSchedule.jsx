import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardContent } from "./ui/Card";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { motion, AnimatePresence } from "framer-motion";
import { Trash2, Plus } from "lucide-react";
import InputField from "./ui/InputField";
import SelectField from "./ui/SelectField";
import TimeRangePicker from "./ui/TimeRangePicker";
import DaySelector from "./ui/DaySelector";
import { validateSchedule } from "../validators/scheduleSchema";

export default function ZoneSchedule({ zones = [], schedules = [], setSchedules }) {
  const [local, setLocal] = useState({
    zone_id: "",
    start_time: "08:00",
    end_time: "18:00",
    temp_min: 19,
    temp_max: 22,
    days: ["monday"],
    timeRanges: [
      { start_time: "08:00", end_time: "18:00" }
    ],
  });

  const [errors, setErrors] = useState({});
  const [valid, setValid] = useState(false);

  // -------------------------------------------------------------
  //  Zonas que tienen al menos una entidad seleccionada
  // -------------------------------------------------------------
  const selectableZones = zones.filter((z) =>
    z.devices?.some((d) =>
      d.entities?.some((e) => e.selected === true)
    )
  );

  /* -------------------------------------------------------------
      Inicializar zone_id cuando llegan las zonas
  ------------------------------------------------------------- */
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (!selectableZones.length || initialized) return;

    setLocal((prev) => ({
      ...prev,
      zone_id: String(selectableZones[0].id),
    }));

    setInitialized(true);
  }, [selectableZones, initialized]);


  // -------------------------------------------------------------
  //  Gestionar time ranges
  // -------------------------------------------------------------
  const addTimeRange = () => {
    setLocal((prev) => ({
      ...prev,
      timeRanges: [
        ...prev.timeRanges,
        { start_time: "08:00", end_time: "18:00" },
      ],
    }));
  };

  const removeTimeRange = (index) => {
    setLocal((prev) => ({
      ...prev,
      timeRanges: prev.timeRanges.filter((_, i) => i !== index),
    }));
  };

  const updateTimeRange = (index, { startTime, endTime }) => {
    setLocal((prev) => {
      const next = [...prev.timeRanges];
      next[index] = {
        start_time: startTime,
        end_time: endTime,
      };
      return { ...prev, timeRanges: next };
    });
  };

  // -------------------------------------------------------------
  //  Helper: expandir local -> array de schedules "simples"
  //  (uno por día y rango)
  // -------------------------------------------------------------
  const buildSchedulesFromLocal = (data) => {
    const { zone_id, days = [], timeRanges = [], temp_min, temp_max } = data;

    if (!zone_id || !days.length || !timeRanges.length) return [];

    const result = [];
    days.forEach((day) => {
      timeRanges.forEach((range) => {
        if (!range.start_time || !range.end_time) return;

        result.push({
          zone_id: zone_id, // lo dejamos como string; el backend lo maneja sin problema
          days: day.toLowerCase(),
          start_time: range.start_time,
          end_time: range.end_time,
          temp_min,
          temp_max,
        });
      });
    });

    return result;
  };


  // -------------------------------------------------------------
  //  Añadir schedules
  // -------------------------------------------------------------
  const addSchedule = async () => {
    const expanded = buildSchedulesFromLocal(local);

    if (!expanded.length) {
      setErrors({
        days: "Select at least one day",
        start_time: "Add at least one valid time range",
      });
      return;
    }

    let aggregatedErrors = {};
    for (const sched of expanded) {
      const { valid, errors } = await validateSchedule(sched);
      if (!valid) {
        aggregatedErrors = { ...aggregatedErrors, ...errors };
      }
    }

    if (Object.keys(aggregatedErrors).length > 0) {
      setErrors(aggregatedErrors);
      return;
    }

    setSchedules([...schedules, ...expanded]);
    setErrors({});

    // Reset suave manteniendo la zona
    setLocal((prev) => ({
      ...prev,
      days: ["monday"],
      timeRanges: [{ start_time: "08:00", end_time: "18:00" }],
      temp_min: 19,
      temp_max: 22,
    }));
  };

  const removeSchedule = (idx) =>
    setSchedules(schedules.filter((_, i) => i !== idx));

  // Map para mostrar nombre de zona en la lista
  const zoneNameMap = new Map(
    (zones || []).map((z) => [String(z.id), z.name])
  );

  return (
    <Card className="w-full shadow-xl rounded-2xl p-4 space-y-6">
      <CardHeader>
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Badge variant="secondary" className="px-3 py-1 text-sm">
            Scheduler
          </Badge>
          Zone & Temperature Planner
        </h2>
      </CardHeader>

      <CardContent className="space-y-4">

        {/* -------------------- SELECTORS -------------------- */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

          {/* ZONE SELECT */}
          <SelectField
            label="Zone"
            value={local.zone_id}
            onChange={(e) => setLocal({ ...local, zone_id: Number(e.target.value) })}
            options={zones
              .sort((a, b) => a.name.localeCompare(b.name))
              .map((z) => ({ value: z.id, label: z.name }))}
          />
          {errors.zone_id && (
            <span className="text-red-500 text-sm">{errors.zone_id}</span>
          )}
        </div>

        {/* DAYS */}
        <DaySelector
          label="Days"
          selectedDays={local.days}
          onChange={(days) => setLocal({ ...local, days })}
        />
        {errors.days && (
          <span className="text-red-500 text-sm">{errors.days}</span>
        )}

        {/* TIME RANGE */}
        <div className="space-y-2">
          {local.timeRanges.map((range, idx) => (
            <TimeRangePicker
              key={idx}
              label={idx === 0 ? "Time Ranges" : ""}
              startTime={range.start_time}
              endTime={range.end_time}
              onChange={(val) => updateTimeRange(idx, val)}

              // nuevo:
              isLast={idx === local.timeRanges.length - 1}
              onAdd={addTimeRange}
              canRemove={local.timeRanges.length > 1}
              onRemove={() => removeTimeRange(idx)}
            />
          ))}
        </div>

        {(errors.start_time || errors.end_time) && (
          <span className="text-red-500 text-sm">
            {errors.start_time || errors.end_time}
          </span>
        )}


        {/* TEMPERATURES */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <InputField
            label="Min Temperature (°C)"
            type="number"
            value={local.temp_min}
            onChange={(e) =>
              setLocal({ ...local, temp_min: Number(e.target.value) })
            }
          />
          {errors.temp_min && (
            <span className="text-red-500 text-sm">{errors.temp_min}</span>
          )}

          <InputField
            label="Max Temperature (°C)"
            type="number"
            value={local.temp_max}
            onChange={(e) =>
              setLocal({ ...local, temp_max: Number(e.target.value) })
            }
          />
          {errors.temp_max && (
            <span className="text-red-500 text-sm">{errors.temp_max}</span>
          )}
        </div>

        {/* ADD BUTTON */}
        <Button
          className={`rounded-xl md:w-auto"
            }`}
          disabled={!local.zone_id || !local.days.length || !local.timeRanges.length}
          onClick={addSchedule}
        >
          Add Schedule
        </Button>

        {/* -------------------- LISTA DE SCHEDULES -------------------- */}
        <div className="space-y-3 mt-4">
          <h3 className="font-medium text-lg">Added Schedules</h3>

          <AnimatePresence>
            {schedules.map((s, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2 }}
                className="flex items-center justify-between p-3 rounded-xl border shadow-sm bg-white dark:bg-gray-850"
              >
                <div className="flex flex-col gap-1">
                  <span className="font-medium capitalize">{s.days}</span>
                  <span className="text-sm opacity-70">
                    {s.start_time} - {s.end_time} | Zone {zoneNameMap.get(String(s.zone_id))}
                  </span>
                  <Badge variant="outline" className="w-fit mt-1">
                    {s.temp_min}°C → {s.temp_max}°C
                  </Badge>
                </div>

                <Button
                  variant="ghost"
                  size="icon"
                  className="!p-0 !px-0 !py text-red-500 hover:text-red-700"
                  onClick={() => removeSchedule(idx)}
                >
                  <Trash2 className="h-5 w-5" />
                </Button>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </CardContent>
    </Card>
  );
}
