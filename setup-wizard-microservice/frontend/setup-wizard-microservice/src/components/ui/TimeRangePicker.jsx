import React from "react";
import { Trash2, Plus } from "lucide-react";
import { Button } from "./Button";
import InputField from "./InputField";

export default function TimeRangePicker({ startTime, endTime, onChange, label = "Time Range", error = "", onAdd, onRemove, isLast = false, canRemove = false, }) {
  const handleStartChange = (e) => onChange({ startTime: e.target.value, endTime });
  const handleEndChange = (e) => onChange({ startTime, endTime: e.target.value });

  return (
    <div className="flex flex-col mb-2 w-full">
      {label && (
        <label className="mb-1 font-medium text-gray-900 dark:text-gray-100">
          {label}
        </label>
      )}

      <div className="flex gap-2 items-end">

        {/* ------ Time Inputs ------ */}
        <div className="flex-1 flex gap-2">
          <InputField
            type="time"
            value={startTime}
            onChange={handleStartChange}
            className="flex-1"
          />

          <span className="flex items-center text-gray-500 dark:text-gray-400">
            to
          </span>

          <InputField
            type="time"
            value={endTime}
            onChange={handleEndChange}
            className="flex-1"
          />

          {/* ------ ADD BUTTON (+) ------ */}
          {isLast && onAdd && (
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="w-8 h-8 p-1 flex items-center justify-center"
              onClick={onAdd}
            >
              <Plus className="w-4 h-4 text-gray-700 dark:text-gray-200" />
            </Button>
          )}

          {/* ------ REMOVE BUTTON (🗑) ------ */}
          {canRemove && onRemove && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="w-8 h-8 p-1 flex items-center justify-center text-red-500 hover:text-red-700"
              onClick={onRemove}
            >
              <Trash2 className="w-4 h-4 text-red-500" />
            </Button>
          )}
        </div>
        
      </div>

      {error && <span className="mt-1 text-xs text-red-500">{error}</span>}
    </div>
  );
}