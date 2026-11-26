"""Índice único case-insensitive para o e-mail do User.

Garante no banco a regra que os serializers aplicam na aplicação: dois usuários
não podem ter o mesmo e-mail ignorando maiúsculas/minúsculas. O índice é parcial
(só e-mails não vazios), porque o User do Django permite e-mail em branco e não
faria sentido bloquear vários usuários sem e-mail.

Criado com RunSQL (com reverse_sql) porque é um índice em expressão LOWER(email)
sobre a tabela auth_user — modelo que não pertence a este app. Depende da última
migration do app auth para garantir que auth_user já exista no estado migrado.

ATENÇÃO (produção): NÃO aplicar antes de remover e-mails duplicados existentes no
banco; a criação do índice falha se houver duplicatas. Em produção os duplicados
devem ser resolvidos manualmente no Neon antes do migrate.
"""

from django.db import migrations

INDEX_NAME = "auth_user_email_ci_unique"

CREATE_INDEX_SQL = (
    f'CREATE UNIQUE INDEX "{INDEX_NAME}" ON "auth_user" (LOWER("email")) '
    "WHERE \"email\" <> '';"
)

DROP_INDEX_SQL = f'DROP INDEX IF EXISTS "{INDEX_NAME}";'


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunSQL(
            sql=CREATE_INDEX_SQL,
            reverse_sql=DROP_INDEX_SQL,
        ),
    ]
