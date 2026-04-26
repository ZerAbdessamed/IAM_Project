from marshmallow import Schema, ValidationError, fields, validate


class AdminRegisterSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))
    email = fields.Email(required=True)
    full_name = fields.Str(required=True, validate=validate.Length(min=3, max=120))
    password = fields.Str(required=True, validate=validate.Length(min=8, max=255))
    bootstrap_key = fields.Str(load_default=None)


class AdminLoginSchema(Schema):
    username_or_email = fields.Str(required=True, validate=validate.Length(min=3, max=120))
    password = fields.Str(required=True, validate=validate.Length(min=1, max=255))


class ChangePasswordSchema(Schema):
    current_password = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    new_password = fields.Str(required=True, validate=validate.Length(min=8, max=255))
    confirm_password = fields.Str(required=True, validate=validate.Length(min=8, max=255))


class ResetPasswordSchema(Schema):
    email = fields.Email(required=True)


class IdentityApiSchema(Schema):
    user_type = fields.Str(
        required=True,
        validate=validate.OneOf(["student", "faculty", "staff", "external"]),
    )
    first_name = fields.Str(required=True, validate=validate.Length(min=2, max=80))
    last_name = fields.Str(required=True, validate=validate.Length(min=2, max=80))
    date_of_birth = fields.Str(required=True)
    place_of_birth = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    nationality = fields.Str(required=True, validate=validate.Length(min=2, max=80))
    gender = fields.Str(required=True, validate=validate.Length(min=1, max=24))
    personal_email = fields.Email(required=True)
    phone_number = fields.Str(required=True, validate=validate.Length(min=6, max=20))
    password = fields.Str(required=True, validate=validate.Length(min=8, max=255))
    conf_password = fields.Str(required=True, validate=validate.Length(min=8, max=255))


def validate_json_payload(schema_cls, payload):
    try:
        return schema_cls().load(payload)
    except ValidationError as exc:
        raise ValueError(exc.messages) from exc
