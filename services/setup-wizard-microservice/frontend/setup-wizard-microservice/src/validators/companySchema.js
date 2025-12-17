import * as yup from "yup";

export const companySchema = yup.object().shape({
    name: yup.string().required("Company name is required").min(2),
    address: yup.string().required("Address is required").min(5),
    phone: yup
        .string()
        .matches(/^[0-9+\-() ]+$/, "Phone number is not valid")
        .required(),
    email: yup.string().email().required(),
    config_name: yup.string().required().default("Default"),
});

export const validateCompany = async (data) => {
    try {
        await companySchema.validate(data, { abortEarly: false });
        return { valid: true, errors: {} };
    } catch (err) {
        const errors = {};
        if (err.inner) {
            err.inner.forEach((e) => {
                errors[e.path] = e.message;
            });
        }
        return { valid: false, errors };
    }
};