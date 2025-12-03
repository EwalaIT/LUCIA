import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import BackButton from "./ui/BackButton"
import CompanyForm from "./CompanyForm";
import EntitySelectorTree from "./EntitySelector";
import ZoneSchedule from "./ZoneSchedule";
import ConfirmationModal from "./ConfirmationModal";
import {
  loadSetupSchedules,
  saveSetupSchedules,
  updateSelectedEntities,
} from "../services/schedulesService";
import { getHaSummary } from "../services/zonesService";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080/api";

export default function SetupWizard() {
  const [step, setStep] = useState(1);

  // Home Assistant summary structure:
  // { devices: [], entities: [], areas: [] }
  const [haSummary, setHaSummary] = useState({
    devices: [],
    entities: [],
    areas: [],
  });

  const [companyResp, setCompanyResp] = useState(null);
  const [selectedEntities, setSelectedEntities] = useState(new Set());
  const [schedules, setSchedules] = useState([]);

  const [modalOpen, setModalOpen] = useState(false);
  const [action, setAction] = useState(null);

  /* -----------------------------------------------
       Navigation Logic
  ------------------------------------------------ */
  const handleNext = () => {
    if (step === 1) {
      return; // Step 1 avanza desde CompanyForm solo
    }

    if (step === 2) {
      // Confirmar selección de entidades
      setAction("saveEntities");
      setModalOpen(true);
      return;
    }

    if (step === 3) {
      // Confirmar guardar schedules
      setAction("saveSchedules");
      setModalOpen(true);
    }
  };

  const handleCancel = () => {
    setAction("cancel");
    setModalOpen(true);
  };

  /* -----------------------------------------------
      Confirm modal actions
  ------------------------------------------------ */
  const handleConfirm = async () => {
    try {
      if (action === "saveEntities") {
        await updateSelectedEntities(selectedEntities);
        setStep(3);
      } else if (action === "saveSchedules") {
        await saveSetupSchedules(schedules);
        alert("Configuration saved successfully!");
        window.location.href = "http://192.168.230.142:3090/c/new";
      } else if (action === "cancel") {
        setStep(1);
        setCompanyResp(null);
        setSelectedEntities(new Set());
        setSchedules([]);
      }
    } catch (err) {
      alert("Error: " + err.message);
    }

    setModalOpen(false);
  };

  const steps = ["Company Info", "Entity Selection", "Schedules"];

  /* -----------------------------------------------
        RENDER
  ------------------------------------------------ */
  return (
    <div className="bg-white dark:bg-gray-900 shadow-xl rounded-2xl p-6 w-full max-w-4xl mx-auto">

      {/* Stepper */}
      <div className="flex justify-between mb-6">
        {steps.map((label, index) => {
          const num = index + 1;
          return (
            <div key={num} className="flex-1 text-center">
              <div
                className={`
                  w-10 h-10 mx-auto rounded-full flex items-center justify-center text-white
                  ${step === num ? "bg-blue-600" :
                    step > num ? "bg-green-500" :
                      "bg-gray-400 dark:bg-gray-700"}
                `}
              >
                {num}
              </div>
              <div className="text-sm mt-1 text-gray-600 dark:text-gray-300">
                {label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Animated Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 40 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -40 }}
          transition={{ duration: 0.25 }}
        >
          {/* STEP 1: COMPANY */}
          {step === 1 && (
            <CompanyForm
              apiBase={API_BASE}
              onSaved={async (resp) => {
                try {
                  setCompanyResp(resp);

                  const summary = await getHaSummary();

                  if (!summary || typeof summary !== "object") {
                    throw new Error("Invalid HA summary response");
                  }

                  // Ensure the structure is correct
                  setHaSummary({
                    devices: summary.devices || [],
                    entities: summary.entities || [],
                    areas: summary.zones || [],
                  });

                  setStep(2);
                } catch (error) {
                  console.error("HA Summary Load Failed:", error);
                  alert("No se pudo cargar la información de Home Assistant.");
                }
              }}
            />
          )}

          {/* STEP 2: ENTITY SELECTION (BY AREAS) */}
          {step === 2 && haSummary.areas && (
            <EntitySelectorTree
              data={{ areas: haSummary.areas }}
              selected={selectedEntities}
              setSelected={setSelectedEntities}
            />
          )}

          {/* STEP 3: SCHEDULES */}
          {step === 3 && (
            <ZoneSchedule
              zones={haSummary.areas}
              schedules={schedules}
              setSchedules={setSchedules}
            />
          )}
        </motion.div>
      </AnimatePresence>

      {/* Bottom Buttons */}
      <div className="flex justify-end gap-3 mt-8">
        <button
          className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700
                     hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          onClick={handleCancel}
        >
          Cancel
        </button>

        <button
          className="px-6 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition"
          disabled={step === 1}
          onClick={handleNext}
        >
          {step < 3 ? "Next" : "Finish"}
        </button>
      </div>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={
          action === "cancel"
            ? "Confirm Cancel"
            : action === "saveEntities"
              ? "Confirm Entity Selection"
              : "Confirm Save Schedules"
        }
        description={
          action === "cancel"
            ? "Are you sure you want to cancel the setup? All progress will be lost."
            : action === "saveEntities"
              ? "Do you want to save the selected Home Assistant entities?"
              : "Do you want to save all configured schedules?"
        }
        onConfirm={handleConfirm}
      />
    </div>
  );
}
