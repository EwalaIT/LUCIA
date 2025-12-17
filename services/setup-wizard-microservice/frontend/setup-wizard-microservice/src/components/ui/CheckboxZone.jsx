import React from "react";
import { CheckboxBase } from "./CheckboxBase";

export function CheckboxZone({ checked, indeterminate, onChange, disabled = false }) {
    return (
        <CheckboxBase
            checked={checked}
            indeterminate={indeterminate}
            onChange={onChange}
            disabled={disabled}
            size="lg"
            className="shadow"
        />
    );
}
