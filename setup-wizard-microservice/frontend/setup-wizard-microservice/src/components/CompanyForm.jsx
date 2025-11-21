import React, { useState, useEffect } from "react";
import { saveCompany, loadCompany } from "../services/schedulesService";
import { validateCompany } from "../validators/companySchema";

export default function CompanyForm({ onSaved }) {
  const [form, setForm] = useState({
    name: "",
    address: "",
    phone: "",
    email: "",
    city: "",
    country: "",
    config_name: "Default",
  });

  const [original, setOriginal] = useState(null); // Para detectar cambios
  const [errors, setErrors] = useState({});
  const [valid, setValid] = useState(false);
  const [loading, setLoading] = useState(true);

  /** -------------------------------------------------------------
   * 1. Cargar la compañía existente (si la hay)
   * ------------------------------------------------------------- */
  useEffect(() => {
    const fetchCompany = async () => {
      try {
        const resp = await loadCompany();
        if (resp.exists && resp.company) {
          const c = resp.company;
          setForm((prev) => ({
            ...prev,
            name: c.name || "",
            address: c.address || "",
            phone: c.phone || "",
            email: c.email || "",
            city: c.city || "",
            country: c.country || "",
          }));
        }
      } catch (err) {
        console.error("Error loading company:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchCompany();
  }, []);

  /** -------------------------------------------------------------
   * 2. Validar formulario cada vez que cambie
   * ------------------------------------------------------------- */
  useEffect(() => {
    const checkValid = async () => {
      const { valid, errors } = await validateCompany(form);
      setValid(valid);
      setErrors(errors);
    };
    checkValid();
  }, [form]);

  /** -------------------------------------------------------------
   * 3. Actualizar campos
   * ------------------------------------------------------------- */
  const update = (field, value) => {
    setForm({ ...form, [field]: value });
  };

  /** -------------------------------------------------------------
   * 4. Guardar (crear o actualizar)
   * ------------------------------------------------------------- */
  const save = async () => {
    try {
      const { valid, errors } = await validateCompany(form);
      setErrors(errors);
      if (!valid) return;

      const resp = await saveCompany(form);
      onSaved(resp);
    } catch (err) {
      alert("Error: " + err.message);
    }
  };


  if (loading) {
    return (
      <div className="text-gray-500 text-center py-8">
        Loading company data…
      </div>
    );
  }

  /** -------------------------------------------------------------
   * 5. UI
   * ------------------------------------------------------------- */
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-medium text-gray-800 mb-4">
        Company Information
      </h2>

      <div>
        <label className="block text-sm font-medium mb-1">Company Name</label>
        <input
          className={`input ${errors.name ? "border-red-500" : ""}`}
          value={form.name}
          onChange={(e) => update("name", e.target.value)}
        />
        {errors.name && (
          <span className="text-red-500 text-sm">{errors.name}</span>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">Address</label>
        <input
          className={`input ${errors.address ? "border-red-500" : ""}`}
          value={form.address}
          onChange={(e) => update("address", e.target.value)}
        />
        {errors.address && (
          <span className="text-red-500 text-sm">{errors.address}</span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Phone</label>
          <input
            className={`input ${errors.phone ? "border-red-500" : ""}`}
            value={form.phone}
            onChange={(e) => update("phone", e.target.value)}
          />
          {errors.phone && (
            <span className="text-red-500 text-sm">{errors.phone}</span>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Email</label>
          <input
            className={`input ${errors.email ? "border-red-500" : ""}`}
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
          />
          {errors.email && (
            <span className="text-red-500 text-sm">{errors.email}</span>
          )}
        </div>
      </div>

      {/* Opcional: city / country si quieres mostrarlos */}
      {/* 
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">City</label>
          <input
            className="input"
            value={form.city}
            onChange={(e) => update("city", e.target.value)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Country</label>
          <input
            className="input"
            value={form.country}
            onChange={(e) => update("country", e.target.value)}
          />
        </div>
      </div>
      */}

      <button
        onClick={save}
        className={`px-5 py-2 rounded-lg transition ${valid
            ? "bg-green-600 hover:bg-green-700 text-white"
            : "bg-gray-300 text-gray-600 cursor-not-allowed"
          }`}
        disabled={!valid}
      >
        Save and Continue
      </button>
    </div>
  );
}