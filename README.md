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
- O backend renderiza páginas HTML com templates do Django. **Não há API JSON** (REST/GraphQL) por enquanto.
- Os arquivos `tests.py` das apps ainda estão vazios.

---

## Stack

| Tecnologia | Uso |
|---|---|
| Python 3.12+ | Linguagem (o Django 6.1 exige 3.12 ou superior) |
| Django 6.1 | Framework web |
| Pillow | Campos de imagem e redimensionamento da foto de perfil |
| SQLite | Banco padrão fora do Docker |
| PostgreSQL 17 | Banco usado no Docker Compose |
| psycopg 3 | Driver do PostgreSQL |

As dependências estão em `requirements.txt`.

---

## Estrutura

```text
django-blog/
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .dockerignore
├── .gitignore
├── .gitattributes
└── django_project/
    ├── manage.py
    ├── django_project/          # configurações globais
    │   ├── settings.py
    │   ├── urls.py
    │   ├── asgi.py
    │   └── wsgi.py
    ├── blog/                    # app do blog
    │   ├── migrations/
    │   ├── templates/blog/
    │   ├── models.py            # Post, Comment, Tag
    │   ├── views.py
    │   └── urls.py
    ├── users/                   # app de usuários
    │   ├── migrations/
    │   ├── templates/users/
    │   ├── forms.py
    │   ├── models.py            # Profile (1-para-1 com User)
    │   └── views.py
    └── media/
        └── profile_pics/
            └── default.jpg      # imagem padrão do perfil (obrigatória)
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

cd django_project
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

## Testes

```bash
cd django_project
python manage.py test
```

Ainda não há testes escritos nas apps `blog` e `users`.

---

## Solução de problemas

**`TemplateDoesNotExist: users/profile.html` ao abrir `/profile/` (Linux, macOS e Docker).**
A view pede `users/profile.html`, mas o arquivo foi versionado como `Profile.html` (com P maiúsculo). O Windows ignora a diferença de maiúsculas; Linux e Docker, não. Renomeie o arquivo no Git (em duas etapas, porque o Windows não percebe a troca só de maiúscula):

```bash
git mv django_project/users/templates/users/Profile.html django_project/users/templates/users/tmp.html
git mv django_project/users/templates/users/tmp.html django_project/users/templates/users/profile.html
```

**`FileNotFoundError: ... media/profile_pics/default.jpg` ao criar um usuário.**
O `Profile` precisa da imagem padrão. Mantenha o `django_project/media/profile_pics/default.jpg` no repositório (o `.gitignore` já o preserva).

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
docker compose cp dados.json backend:/app/django_project/dados.json
docker compose exec backend python manage.py loaddata dados.json
```

As fotos de perfil não vão no `dados.json`: copie também os arquivos de `django_project/media/profile_pics/`.

**E-mails de recuperação de senha não chegam.**
O backend usa o e-mail por console. O conteúdo aparece em `docker compose logs backend` (ou no terminal do `runserver`).

---

## Observações de segurança

- O `.gitignore` inclui `.env` e `*.sqlite3`. Se `db.sqlite3`, `__pycache__/` ou fotos de usuários já foram commitados, remova-os do índice sem apagar os arquivos locais:

  ```bash
  git rm -r --cached django_project/db.sqlite3 django_project/media/profile_pics/megumin_2.jpg
  git rm -r --cached --ignore-unmatch "*/__pycache__/*"
  ```

- A `SECRET_KEY` antiga ficou no histórico do Git. Se o projeto for publicado, gere uma nova e use `DJANGO_SECRET_KEY`.
- O setup deste repositório é para **desenvolvimento** (`runserver`). Para produção, use um servidor WSGI/ASGI (como o Gunicorn), `DJANGO_DEBUG=false`, `collectstatic` e um proxy como o nginx.

---

## Licença

MIT.