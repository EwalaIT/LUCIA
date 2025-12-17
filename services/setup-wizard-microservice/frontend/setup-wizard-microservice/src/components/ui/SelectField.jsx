import React from "react";

export default function SelectField({
  label,
  options = [],
  value,
  onChange,
  placeholder = "Select...",
  required = false,
  error = "",
  className = "",
  ...props
}) {
  return (
    <div className={`flex flex-col mb-4 ${className}`}>
      {label && (
        <label className="mb-1 font-medium text-gray-900 dark:text-gray-100">
          {label} {required && <span className="text-red-500">*</span>}
        </label>
      )}
      <select
        value={value}
        onChange={onChange}
        required={required}
        className={`px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-700
          bg-white dark:bg-gray-850 text-gray-900 dark:text-gray-100
          focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400
          transition-colors duration-150 ${error ? "border-red-500" : ""}`}
        {...props}
      >
        <option value="" disabled>{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      {error && <span className="mt-1 text-xs text-red-500">{error}</span>}
    </div>
  );
}
