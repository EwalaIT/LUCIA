import * as yup from "yup";

export const daysOfWeek = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
];

export const scheduleSchema = yup.object().shape({
    zone_id: yup.string().required("Area is required"),

    days: yup.string().oneOf(daysOfWeek).required(),

    start_time: yup
        .string()
        .matches(/^([0-1]\d|2[0-3]):([0-5]\d)$/)
        .required(),

    end_time: yup
        .string()
        .matches(/^([0-1]\d|2[0-3]):([0-5]\d)$/)
        .required()
        .test("after-start", "End time must be after start", function (value) {
            const { start_time } = this.parent;
            return value > start_time;
        }),

    temp_min: yup.number().min(0).required(),
    temp_max: yup.number().moreThan(yup.ref("temp_min")).required(),
});

export const validateSchedule = async (data) => {
    try {
        await scheduleSchema.validate(data, { abortEarly: false });
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
