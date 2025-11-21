import React from "react";
import { CheckboxBase } from "./CheckboxBase";

export function CheckboxEntity({ checked, onChange, disabled = false }) {
    return (
        <CheckboxBase
            checked={checked}
            onChange={onChange}
            disabled={disabled}
            size="sm"
            className="shadow-sm"
        />
    );
}
