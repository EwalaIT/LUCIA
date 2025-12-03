import React from 'react';
import { Routes, Route } from "react-router-dom"
import BackButton from "./components/ui/BackButton"
import SetupWizard from "./components/SetupWizard"
import DecisionsManager from "./components/DecisionsManager"
import RulesManager from "./components/RulesManager"

export default function App() {

  return (
      <div className="min-h-screen bg-gray-100 p-8 flex justify-center">
        <div className="w-full max-w-4xl">
          <Routes>
            <Route
              path="/"
              element={
                <div className="w-full max-w-4xl mx-auto">
                  <BackButton label="Back to Dashboard" />
                  <h1 className="text-3xl font-semibold text-gray-800 mb-6">
                    LUCIA Setup Wizard
                  </h1>
                  <SetupWizard />
                </div>
              }
            />
            <Route path="/decisions" element={<DecisionsManager />} />
            <Route path="/rules" element={<RulesManager />} />
          </Routes>
        </div>
      </div>
  );
}

