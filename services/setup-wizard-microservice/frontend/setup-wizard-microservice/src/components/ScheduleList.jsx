// components/ScheduleList.jsx
import React from "react";
import { AnimatePresence } from "framer-motion";
import ScheduleItem from "./ScheduleItem";
import { useZonesStore } from "../store/useZonesStore";

export default function ScheduleList() {
  const { schedules, removeSchedule, updateSchedule } = useZonesStore();

  const handleEdit = (schedule) => {
    // Open an edit modal in your app; for now, we provide a simple prompt example.
    // Ideally implement a modal with a proper form and validation.
    const newMin = prompt("New min temp (ºC):", schedule.temp_min);
    const newMax = prompt("New max temp (ºC):", schedule.temp_max);
    if (newMin == null || newMax == null) return;
    const updated = { temp_min: parseFloat(newMin), temp_max: parseFloat(newMax) };
    updateSchedule(schedule.id, updated).catch((err) => {
      alert("Failed to update schedule: " + err.message);
    });
  };

  const handleDelete = (id) => {
    if (!window.confirm("Are you sure you want to delete this schedule?")) return;
    removeSchedule(id).catch((err) => {
      alert("Failed to delete schedule: " + err.message);
    });
  };

  if (!schedules || schedules.length === 0) {
    return <div className="text-gray-500 dark:text-gray-400 mt-2">No schedules added yet.</div>;
  }

  // sort schedules (day + start_time)
  const days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
  const sorted = [...schedules].sort((a, b) => {
    const dayDiff = days.indexOf(a.day_of_week?.toLowerCase() || "") - days.indexOf(b.day_of_week?.toLowerCase() || "");
    if (dayDiff !== 0) return dayDiff;
    return (a.start_time || "").localeCompare(b.start_time || "");
  });


  return (
    <div className="space-y-2 mt-2">
      <AnimatePresence>
        {sorted.map((s) => (
          <ScheduleItem
            key={s.id || `${s.zone_id}-${s.day_of_week}-${s.start_time}`}
            schedule={s}
            onEdit={() => handleEdit(s)}
            onDelete={() => handleDelete(s.id)}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
