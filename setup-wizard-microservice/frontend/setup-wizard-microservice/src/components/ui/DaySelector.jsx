import React from "react";

const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

export default function DaySelector({ selectedDays = [], onChange, label = "Select Days" }) {
  const toggleDay = (day) => {
    onChange(
      selectedDays.includes(day)
        ? selectedDays.filter((d) => d !== day)
        : [...selectedDays, day]
    );
  };

  return (
    <div className="flex flex-col mb-4">
      {label && (
        <label className="mb-1 font-medium text-gray-900 dark:text-gray-100">
          {label}
        </label>
      )}
      <div className="flex flex-wrap gap-2">
        {DAYS.map((day) => {
          const label = day.charAt(0).toUpperCase() + day.slice(1);

          return (
            <button
              key={day}
              type="button"
              onClick={() => toggleDay(day)}
              className={`px-3 py-1 rounded-xl border font-medium text-sm transition-colors duration-150
              ${selectedDays.includes(day)
                  ? "bg-blue-500 border-blue-500 text-white"
                  : "bg-white dark:bg-gray-850 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800"
                }`}
            >
              {label.slice(0, 3)} 
            </button>
          );
        })}
      </div>
    </div>
  );
}
