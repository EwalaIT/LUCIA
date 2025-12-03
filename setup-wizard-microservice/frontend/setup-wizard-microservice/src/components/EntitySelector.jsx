import React, { useState } from "react";
import { CheckboxZone } from "./ui/CheckboxZone";
import { CheckboxDevice } from "./ui/CheckboxDevice";
import { CheckboxEntity } from "./ui/CheckboxEntity";
import { ChevronDown, ChevronRight } from "lucide-react";

/* -------------------------
   Helper: Tri-state resolve
-------------------------- */
const resolveState = (entities, selectedSet) => {
  if (!entities.length) return "unchecked";

  const selectedCount = entities.filter((e) => selectedSet.has(e.id)).length;

  if (selectedCount === 0) return "unchecked";
  if (selectedCount === entities.length) return "checked";
  return "indeterminate";
};

/* ---------------------------------------------------------
   MAIN COMPONENT
--------------------------------------------------------- */
export default function EntitySelectorTree({ data, selected, setSelected }) {
  const [expandedAreas, setExpandedAreas] = useState({});
  const [expandedDevices, setExpandedDevices] = useState({});

  const toggleAreaExpand = (areaId) =>
    setExpandedAreas((p) => ({ ...p, [areaId]: !p[areaId] }));

  const toggleDeviceExpand = (deviceId) =>
    setExpandedDevices((p) => ({ ...p, [deviceId]: !p[deviceId] }));

  // Toggle entity
  const toggleEntity = (entityId) => {
    const s = new Set(selected);
    s.has(entityId) ? s.delete(entityId) : s.add(entityId);
    setSelected(s);
  };

  // Toggle all entities of a device
  const toggleDeviceEntities = (device) => {
    const all = device.entities.map((e) => e.id);
    const curr = new Set(selected);

    const state = resolveState(device.entities, selected);

    if (state === "checked") all.forEach((id) => curr.delete(id));
    else all.forEach((id) => curr.add(id));

    setSelected(curr);
  };

  // Toggle all entities of an area
  const toggleAreaEntities = (area) => {
    const all = area.devices.flatMap((d) => d.entities.map((e) => e.id));
    const curr = new Set(selected);

    const state = resolveState(all.map((id) => ({ id })), selected);

    if (state === "checked") all.forEach((id) => curr.delete(id));
    else all.forEach((id) => curr.add(id));

    setSelected(curr);
  };

  const areas = data?.areas || [];

  return (
    <div className="w-full bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-700 shadow-lg p-4">
      <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
        Select Home Assistant Entities
      </h2>

      <div className="space-y-3">
        {data.areas?.map((area) => {
          const areaEntities = area.devices.flatMap((d) => d.entities);
          const areaState = resolveState(areaEntities, selected);

          return (
            <div key={area.id} className="border border-gray-300 dark:border-gray-700 rounded-lg">

              {/* AREA HEADER */}
              <div
                className="flex items-center gap-4 p-4 cursor-pointer bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                onClick={() => toggleAreaExpand(area.id)}
              >
                <CheckboxZone
                  checked={areaState === "checked"}
                  indeterminate={areaState === "indeterminate"}
                  onChange={() => toggleAreaEntities(area)}
                />

                <span className="font-semibold text-gray-700 dark:text-gray-200">
                  {area.name}
                </span>

                <div className="ml-auto">
                  {expandedAreas[area.id] ? (
                    <ChevronDown className="w-5 h-5 opacity-70" />
                  ) : (
                    <ChevronRight className="w-5 h-5 opacity-70" />
                  )}
                </div>
              </div>

              {/* DEVICE LIST */}
              {expandedAreas[area.id] && (
                <div className="pl-6 py-3 space-y-3 border-t border-gray-200 dark:border-gray-700">
                  {area.devices.map((device) => {
                    const state = resolveState(device.entities, selected);

                    return (
                      <div key={device.id} className="border rounded-md dark:border-gray-700">

                        {/* DEVICE HEADER */}
                        <div
                          className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800"
                          onClick={() => toggleDeviceExpand(device.id)}
                        >
                          <CheckboxDevice
                            checked={state === "checked"}
                            indeterminate={state === "indeterminate"}
                            onChange={() => toggleDeviceEntities(device)}
                          />

                          <span className="text-gray-700 dark:text-gray-200">
                            {device.name}
                          </span>

                          <div className="ml-auto">
                            {expandedDevices[device.id] ? (
                              <ChevronDown className="w-4 h-4 opacity-70" />
                            ) : (
                              <ChevronRight className="w-4 h-4 opacity-70" />
                            )}
                          </div>
                        </div>

                        {/* ENTITY LIST */}
                        {expandedDevices[device.id] && (
                          <div className="pl-6 py-2 space-y-1 border-t border-gray-100 dark:border-gray-700">
                            {device.entities.map((entity) => (
                              <div
                                key={entity.id}
                                className="flex items-center gap-3 px-3 py-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
                              >
                                <CheckboxEntity
                                  checked={selected.has(entity.id)}
                                  onChange={() => toggleEntity(entity.id)}
                                />

                                <span className="text-gray-600 dark:text-gray-300">
                                  {entity.friendly_name}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}

                  {expandedAreas[area.id] && area.entities_without_device?.length > 0 && (
                    <div className="pl-6 py-2 space-y-1 border-t border-gray-200 dark:border-gray-700">
                      <div className="text-sm font-semibold text-gray-500 dark:text-gray-400 mb-1">
                        Entities without device
                      </div>
                      {area.entities_without_device.map((entity) => (
                        <div
                          key={entity.id}
                          className="flex items-center gap-3 px-3 py-1 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
                        >
                          <CheckboxEntity
                            checked={selected.has(entity.id)}
                            onChange={() => toggleEntity(entity.id)}
                          />
                          <span className="text-gray-600 dark:text-gray-300">
                            {entity.friendly_name}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
