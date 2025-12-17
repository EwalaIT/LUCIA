// components/ScheduleItem.jsx
import React from "react";
import { motion } from "framer-motion";

export default function ScheduleItem({ schedule, onEdit, onDelete }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex justify-between items-center p-3 bg-white dark:bg-gray-850 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
    >
      <div className="flex flex-col">
        <div className="font-semibold text-gray-800 dark:text-gray-100">
          {schedule.day_of_week} | {schedule.start_time} - {schedule.end_time}
        </div>
        <div className="text-sm text-gray-500 dark:text-gray-400">
          Zone: {schedule.zone_name} | Entity: {schedule.entity_name}
        </div>
        <div className="flex gap-2 mt-1">
          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-100">
            Min: {schedule.temp_min}°C
          </span>
          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100">
            Max: {schedule.temp_max}°C
          </span>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          className="px-3 py-1 bg-yellow-400 hover:bg-yellow-500 text-white rounded-md shadow-sm transition-colors text-sm"
          onClick={() => onEdit(schedule)}
        >
          Edit
        </button>
        <button
          className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded-md shadow-sm transition-colors text-sm"
          onClick={() => onDelete(schedule.id)}
        >
          Delete
        </button>
      </div>
    </motion.div>
  );
}
