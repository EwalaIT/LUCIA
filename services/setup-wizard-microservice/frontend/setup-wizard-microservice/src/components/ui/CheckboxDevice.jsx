import React from "react";
import { CheckboxBase } from "./CheckboxBase";

export function CheckboxDevice({ checked, indeterminate, onChange, disabled = false }) {
    return (
        <CheckboxBase
            checked={checked}
            indeterminate={indeterminate}
            onChange={onChange}
            disabled={disabled}
            size="md"
            className="shadow-sm"
        />
    );
}
