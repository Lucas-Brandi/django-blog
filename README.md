# Django Blog & User System

Aplicação web em **Python** com **Django**, com um blog e um sistema de contas de usuário (cadastro, login, logout, perfil com foto e recuperação de senha por e-mail).

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django)

---

## Funcionalidades

- Página inicial e página "About" do blog (acesso restrito a usuários logados)
- Cadastro, login e logout
- Perfil do usuário com edição de e-mail, bio e foto (a imagem é reduzida para no máximo 400×400)
- Recuperação de senha por e-mail (em desenvolvimento, o e-mail aparece no console)
- Painel administrativo do Django com `Post`, `Comment`, `Tag` e `Profile`

### Estado atual

- A listagem da home usa uma lista fixa em `blog/views.py`. Os models `Post`, `Comment` e `Tag` existem e podem ser editados no admin, mas ainda não são lidos pelas views.
- O backend renderiza páginas HTML com templates do Django e **também expõe uma API REST** (JSON) sob o prefixo `/api/v1/`, consumida pelo front React. A base da API (health check, CORS, paginação e formato de erro) já está no ar; os endpoints de dados chegam nas próximas milestones. As rotas HTML continuam funcionando.
- Os arquivos `tests.py` das apps ainda estão vazios.

---

## Stack

| Tecnologia | Uso |
|---|---|
| Python 3.12+ | Linguagem (o Django 6.1 exige 3.12 ou superior) |
| Django 6.1 | Framework web |
| Django REST Framework | API REST (JSON) sob `/api/v1/` |
| django-cors-headers | Libera o front React (CORS) a consumir a API |
| Pillow | Campos de imagem e redimensionamento da foto de perfil |
| SQLite | Banco padrão fora do Docker |
| PostgreSQL 17 | Banco usado no Docker Compose |
| psycopg 3 | Driver do PostgreSQL |

As dependências de produção estão em `requirements.txt`; as de desenvolvimento (Ruff e Pytest) em `requirements-dev.txt`.

---

## Estrutura

```text
django-blog/
├── README.md
├── requirements.txt             # dependências de produção
├── requirements-dev.txt         # ferramentas de dev (ruff, pytest)
├── pyproject.toml               # configuração do Ruff e do Pytest
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .dockerignore
├── .gitignore
├── .gitattributes
├── manage.py
├── config/                      # configurações globais
│   ├── settings.py
│   ├── urls.py                  # inclui o prefixo /api/v1/
│   ├── api.py                   # health check + formato de erro da API
│   ├── api_urls.py              # rotas da API v1
│   ├── asgi.py
│   └── wsgi.py
├── blog/                        # app do blog
│   ├── migrations/
│   ├── templates/blog/
│   ├── models.py                # Post, Comment, Tag
│   ├── views.py
│   └── urls.py
├── users/                       # app de usuários
│   ├── migrations/
│   ├── templates/users/
│   ├── forms.py
│   ├── models.py                # Profile (1-para-1 com User)
│   └── views.py
└── media/
    └── profile_pics/
        └── default.jpg          # imagem padrão do perfil (obrigatória)
```

---

## Início rápido com Docker

Sobe o Django e o PostgreSQL juntos.

```bash
git clone <url-do-repositorio>
cd django-blog

# 1. Variáveis de ambiente
cp .env.example .env            # PowerShell: Copy-Item .env.example .env
# edite o .env e defina POSTGRES_PASSWORD (e, de preferência, DJANGO_SECRET_KEY)

# 2. Suba os containers (as migrações rodam automaticamente)
docker compose up --build

# 3. Em outro terminal, crie o superusuário
docker compose exec backend python manage.py createsuperuser
```

| Recurso | URL |
|---|---|
| Aplicação | http://localhost:8000/ |
| Admin | http://localhost:8000/admin/ |

Comandos úteis:

```bash
docker compose up -d                                   # segundo plano
docker compose logs -f backend                         # logs (e-mails de reset aparecem aqui)
docker compose exec backend python manage.py migrate   # aplicar migrações
docker compose exec backend python manage.py test      # rodar testes
docker compose exec backend python manage.py shell     # shell do Django
docker compose stop                                    # parar
docker compose down                                    # parar e remover containers
docker compose down -v                                 # idem, apagando também o banco
```

---

## Início rápido sem Docker (SQLite)

Requer Python 3.12 ou superior.

```bash
git clone <url-do-repositorio>
cd django-blog

python -m venv venv
source venv/bin/activate          # Windows (PowerShell): .\venv\Scripts\Activate.ps1

pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Sem a variável `POSTGRES_HOST`, o projeto usa o SQLite (`db.sqlite3`).

---

## Variáveis de ambiente

Definidas no `.env` (modelo em `.env.example`). Todas têm valor padrão para desenvolvimento.

| Variável | Padrão | Descrição |
|---|---|---|
| `DJANGO_SECRET_KEY` | chave de exemplo | Chave secreta. **Obrigatória** quando `DJANGO_DEBUG=false` |
| `DJANGO_DEBUG` | `true` | Modo debug |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Hosts permitidos, separados por vírgula |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | vazio | Origens confiáveis (necessário atrás de HTTPS/proxy) |
| `DJANGO_CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Origens autorizadas a consumir a API via navegador (CORS), separadas por vírgula |
| `DJANGO_API_PAGE_SIZE` | `10` | Tamanho de página padrão da API (paginação) |
| `BACKEND_PORT` | `8000` | Porta no seu computador (Docker) |
| `POSTGRES_DB` / `POSTGRES_USER` | `blog` | Nome do banco e usuário |
| `POSTGRES_PASSWORD` | sem padrão | Senha do banco (obrigatória no Docker) |
| `POSTGRES_HOST` | vazio | Quando definido, o Django usa PostgreSQL em vez de SQLite |

Para gerar uma chave secreta:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Evite o caractere `$` na chave, porque o Docker Compose o interpreta como variável.

---

## API REST

O backend expõe uma API JSON sob o prefixo `/api/v1/`, pensada para o front React (Vite, em `http://localhost:5173`). A base está implementada com o Django REST Framework.

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/health/` | Health check. Responde `200` com `{"status": "ok"}` |

Características da base:

- **CORS:** as origens autorizadas vêm de `DJANGO_CORS_ALLOWED_ORIGINS` (padrão `http://localhost:5173`). Requisições do front pelo navegador não tomam erro de CORS.
- **Paginação:** padrão `PageNumberPagination`, com tamanho de página configurável via `DJANGO_API_PAGE_SIZE` (padrão `10`).
- **Formato de erro consistente:** os erros da API são padronizados no envelope `{"error": {"status": <int>, "detail": <...>}}`.

Teste rápido (com os containers de pé):

```bash
curl http://localhost:8000/api/v1/health/
# {"status": "ok"}
```

As rotas HTML atuais continuam funcionando normalmente; a API é adicional.

---

## Qualidade de código e testes

As ferramentas de desenvolvimento ficam em `requirements-dev.txt` (Ruff para lint/formatação e Pytest para testes). A configuração de ambas está no `pyproject.toml` na raiz.

Instale as dependências de desenvolvimento (com o `venv` ativo):

```bash
pip install -r requirements-dev.txt
```

### Lint e formatação (Ruff)

```bash
ruff check .          # checa o lint (não altera arquivos)
ruff check --fix .    # corrige problemas automaticamente (imports, etc.)
ruff format .         # formata o código
```

O Ruff ignora as pastas `venv` e as `migrations` e organiza os imports (isort) automaticamente.

### Testes (Pytest)

```bash
pytest
```

O `pytest-django` usa `DJANGO_SETTINGS_MODULE = config.settings` e descobre arquivos nos formatos `test_*.py` e `*_test.py` (além do `tests.py` de cada app). Ainda não há testes escritos nas apps `blog` e `users`, então o `pytest` coleta 0 testes por enquanto.

O comando nativo do Django também continua funcionando:

```bash
python manage.py test
```

---

## Solução de problemas

**`FileNotFoundError: ... media/profile_pics/default.jpg` ao criar um usuário.**
O `Profile` precisa da imagem padrão. Mantenha o `media/profile_pics/default.jpg` no repositório (o `.gitignore` já o preserva).

**`ImproperlyConfigured: Defina DJANGO_SECRET_KEY...`.**
Com `DJANGO_DEBUG=false` é obrigatório definir `DJANGO_SECRET_KEY`.

**Porta 8000 em uso.** Altere `BACKEND_PORT` no `.env`.

**`password authentication failed` no Postgres após mudar a senha.**
A senha só é aplicada na criação do volume. Para recomeçar, rode `docker compose down -v` (apaga os dados) e suba de novo.

**Levar os dados do SQLite para o PostgreSQL.**
Antes, ajuste o signal em `users/models.py`. Sem isso, o `loaddata` falha com `UNIQUE constraint failed: users_profile.user_id`, porque o signal cria um `Profile` para cada usuário carregado e entra em conflito com os perfis do arquivo. Adicione o guard no início da função:

```python
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if kwargs.get("raw"):
        return  # carregando fixture (loaddata): não cria Profile automaticamente
    if created:
        Profile.objects.create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
        instance.profile.save()
```

No ambiente antigo (SQLite):

```bash
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > dados.json
```

No Docker, depois de subir os containers e migrar:

```bash
docker compose cp dados.json backend:/app/dados.json
docker compose exec backend python manage.py loaddata dados.json
```

As fotos de perfil não vão no `dados.json`: copie também os arquivos de `media/profile_pics/`.

**E-mails de recuperação de senha não chegam.**
O backend usa o e-mail por console. O conteúdo aparece em `docker compose logs backend` (ou no terminal do `runserver`).

---

## Observações de segurança

- O `.gitignore` inclui `.env` e `*.sqlite3`. Se `db.sqlite3`, `__pycache__/` ou fotos de usuários já foram commitados, remova-os do índice sem apagar os arquivos locais:

  ```bash
  git rm -r --cached db.sqlite3 media/profile_pics/megumin_2.jpg
  git rm -r --cached --ignore-unmatch "*/__pycache__/*"
  ```

- A `SECRET_KEY` antiga ficou no histórico do Git. Se o projeto for publicado, gere uma nova e use `DJANGO_SECRET_KEY`.
- O setup deste repositório é para **desenvolvimento** (`runserver`). Para produção, use um servidor WSGI/ASGI (como o Gunicorn), `DJANGO_DEBUG=false`, `collectstatic` e um proxy como o nginx.

---

## Licença

MIT.