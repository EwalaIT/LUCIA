import React from 'react';
import SetupWizard from "./components/SetupWizard";

export default function App() {

  return (
    <div className="min-h-screen bg-gray-100 p-8 flex justify-center">
      <div className="w-full max-w-4xl">
        <h1 className="text-3xl font-semibold text-gray-800 mb-6">
          LUCIA Setup Wizard
        </h1>
        <SetupWizard />
      </div>
    </div>
  );
}

