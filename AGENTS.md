# AGENTS.md — Django Blog

Guia para agentes de IA que trabalham neste repositório. Leia antes de alterar qualquer coisa.

## 1. Escopo e arquitetura

Projeto Django com um blog e um sistema de contas de usuário (cadastro, login, logout, perfil com foto, recuperação de senha por e-mail).

- **Backend:** Django 6.1, Python 3.12 ou superior (o `venv` atual é 3.13).
- **Banco:** SQLite em desenvolvimento fora do Docker; PostgreSQL 17 no Docker Compose.
- **Imagens:** Pillow (redimensiona a foto de perfil para no máximo 400×400).
- **Renderização:** templates HTML do Django. **Não há API JSON (REST/GraphQL) ainda.**

Antes de alterar qualquer coisa:

1. Leia este arquivo, o `README.md`, o `pyproject.toml` e os arquivos de configuração relevantes.
2. Inspecione a estrutura atual: apps (`blog`, `users`), models, views, URLs, templates, migrations e testes.
3. Entenda os padrões já adotados. Prefira estender o que existe a criar estruturas paralelas.
4. Confira o estado do Git (`git status`) e não sobrescreva alterações do usuário.

Não presuma que um app, model, endpoint ou arquivo existe: confirme no repositório.

### Decisões de projeto (D1, D2)

Decisões transversais que travam várias milestones. Registre-as aqui para não depender de contexto externo.

- **D1 — Autenticação da API:** JWT via `djangorestframework-simplejwt` (login, refresh e logout com blacklist). Resolvida em M2.
- **D2 — Quem pode ler o conteúdo:** **leitura pública**. Posts, tags, comentários e a página Sobre são acessíveis sem login; **escrita, perfil e criação de posts exigem autenticação**. É o comportamento esperado de um blog, simplifica a avaliação do projeto e facilita testar a API. Afeta M4, M12 e M15. Em DRF, o padrão é `IsAuthenticatedOrReadOnly` na leitura/escrita e, para objetos, "só o autor (ou staff)" pode alterar/excluir.

## 2. Estrutura do projeto

O `manage.py` e a pasta de configurações (`config/`) ficam na **raiz** do repositório — não há subpasta `django_project/`.

```text
django-blog/
├── manage.py
├── pyproject.toml          # configuração do Ruff e do Pytest
├── requirements.txt        # dependências de produção
├── requirements-dev.txt    # ferramentas de dev (ruff, pytest)
├── config/                 # settings, urls, wsgi, asgi  (DJANGO_SETTINGS_MODULE = config.settings)
├── blog/
├── users/
└── media/profile_pics/default.jpg
```

## 3. Ambiente e comandos

O fluxo padrão desta máquina é o **venv local no host** (Windows / PowerShell). Ative o ambiente antes de qualquer comando:

```powershell
.\venv\Scripts\Activate.ps1
```

Instale as dependências de desenvolvimento (inclui produção via `-r requirements.txt`):

```powershell
pip install -r requirements-dev.txt
```

Comandos de gerenciamento do Django rodam a partir da raiz (onde está o `manage.py`):

```powershell
python manage.py check
python manage.py showmigrations
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

O `venv` precisa de **Python 3.12+** porque o Django 6.1 o exige. Se o `pip install` falhar com erro de versão, confirme o interpretador do `venv` antes de prosseguir. Não instale dependências globalmente no host para contornar isso.

**Fluxo Docker (opcional).** O projeto também sobe via Docker Compose (Django + PostgreSQL). Quando a tarefa for sobre o ambiente Docker, use o padrão `docker compose exec backend python manage.py <comando>`. No container o `manage.py` fica em `/app/manage.py`.

## 4. Validação obrigatória antes de concluir

**Sempre** rode o lint e os testes antes de dar uma tarefa por concluída. Com o `venv` ativo, a partir da raiz:

```powershell
ruff check .
pytest
python manage.py check
```

Se a alteração envolver models ou migrations, inclua também:

```powershell
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
```

Regras:

- Não afirme que lint ou testes passaram sem executá-los.
- Se algum comando falhar, não declare a tarefa concluída: investigue se a falha veio da sua alteração ou já existia, corrija o que estiver no escopo e informe o resto.
- Violações preexistentes fora do escopo devem ser relatadas separadamente, não escondidas nem atribuídas à alteração atual.

## 5. Git e commits

- **Nunca faça commit por conta própria.** Prepare as alterações e descreva o que mudou; o commit é decisão do usuário.
- Quando o usuário pedir um commit, escreva **mensagens em inglês**.
- Prefira adicionar arquivos específicos a `git add .`, para não incluir mudanças não relacionadas.
- Nunca faça commit de `.env`, `db.sqlite3`, caches (`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`) ou fotos de usuários — o `.gitignore` já cobre isso.
- Não altere a configuração do Git nem use operações destrutivas (`push --force`, `reset --hard`) sem autorização explícita.

## 6. Convenções de código

- **Idioma:** comentários e docstrings podem ficar em português (padrão atual do projeto). **Código em inglês**: nomes de variáveis, funções, classes e — quando a API REST for criada — as **rotas/endpoints em inglês**.
- **Lint e formatação pelo Ruff** (config no `pyproject.toml`): line-length 120, regras `E`/`W`/`F`/`I`, aspas duplas. Ele ignora `venv` e as pastas `migrations`.
  - `ruff check .` — checa
  - `ruff check --fix .` — corrige (imports, etc.)
  - `ruff format .` — formata
  - Não desative regras globalmente só para o lint passar. Revise o diff após qualquer `--fix`.
- Prefira soluções simples e explícitas; evite abstrações prematuras e refatorações amplas não solicitadas.
- Valide entradas, trate erros de forma consistente e aplique autenticação/permissões conforme a operação.
- Evite N+1 queries (`select_related`/`prefetch_related`) e use transações quando a operação exigir atomicidade.

## 7. Testes (pytest + pytest-django)

Configuração no `pyproject.toml`: `DJANGO_SETTINGS_MODULE = config.settings`, descoberta de `test_*.py` / `*_test.py` (além do `tests.py` de cada app), `testpaths = blog, users`.

```powershell
pytest                     # roda tudo
pytest -q                  # saída resumida
pytest blog/test_views.py  # arquivo específico
```

- Ainda não há testes escritos; `pytest` coleta 0 testes por enquanto. Isso é esperado até os primeiros testes serem adicionados.
- Use o banco de testes gerenciado pelo pytest-django; nunca rode testes contra dados reais.
- Testes devem ser determinísticos e independentes da ordem de execução. Faça mock de chamadas externas.
- Para mudanças em models, signals, auth, views ou endpoints, inclua testes de regressão. Não enfraqueça testes só para a suíte passar.

## 8. Migrations: não alterar migrations existentes

**Nunca edite, renomeie, apague ou reescreva uma migration já criada.** Não use `--fake`/`--fake-initial` para mascarar divergências.

Quando uma mudança de model exigir migration:

1. Altere o model.
2. Gere uma **nova** migration: `python manage.py makemigrations`.
3. Revise o arquivo gerado para confirmar que contém só as operações esperadas.
4. Aplique e valide: `python manage.py migrate` e `python manage.py showmigrations`.

Em caso de conflito ou divergência entre models e banco, pare e explique antes de qualquer correção destrutiva.

## 9. Model e signal do `Profile`

Há uma relação 1-para-1 entre o `User` do Django e o `Profile` (em `users/models.py`). O signal `create_or_update_user_profile` (`post_save` em `AUTH_USER_MODEL`) já está implementado e **já é idempotente**:

- Ignora `loaddata` via guard `kwargs.get("raw")` (evita `UNIQUE constraint` em `user_id`).
- Cria o `Profile` só quando `created=True`; nas demais vezes usa `get_or_create`.

Cuidados:

- Não crie um segundo mecanismo de criação automática de `Profile`. Preserve o signal existente e sua idempotência.
- Hoje o signal é registrado por estar em `models.py` (importado pelo Django). O `users/apps.py` não usa `ready()`. Se mover o signal para outro módulo, garanta que ele continue sendo importado uma única vez.
- Não altere relacionamento, cardinalidade ou obrigatoriedade do `Profile` sem entender os impactos no código e no banco.
- Ao mexer nesse fluxo, cubra com testes: criar usuário cria um `Profile`; atualizar usuário não cria outro; recuperar perfil não duplica.

## 10. Templates: nome em minúsculas

- O template de perfil é `users/templates/users/profile.html` (minúsculo). **Não renomeie** para `Profile.html` ou variações com maiúsculas — Docker/Linux usam filesystem sensível a maiúsculas.
- Confira se as referências em views e testes batem exatamente com o nome do arquivo.
- Não mova templates nem reorganize sem necessidade.

## 11. Variáveis de ambiente e Docker

Variáveis do backend devem ser documentadas no `.env.example` **e** declaradas no serviço `backend` do `docker-compose.yml` — não basta adicionar só ao `.env` ou ao código.

Ao adicionar/renomear/remover uma variável:

1. Localize todos os pontos que a consomem.
2. Atualize `.env.example` (sem segredos reais).
3. Atualize `docker-compose.yml` para disponibilizá-la ao `backend`.
4. Atualize a leitura no Django com valores padrão seguros quando fizer sentido.
5. Atualize documentação e testes afetados.
6. Valide: `docker compose config` e `python manage.py check`.

Segurança: nunca coloque senhas, tokens ou chaves reais no código, migrations, testes versionados ou no `docker-compose.yml`. Não imprima segredos em logs. Preserve a distinção entre dev e produção.

## 12. Comunicação e entrega

Na resposta final de cada tarefa, informe:

1. O que mudou e em quais arquivos.
2. Decisões relevantes e impactos na API ou no banco.
3. Migrations novas criadas, deixando explícito que as antigas foram preservadas.
4. Resultado do `ruff check .`.
5. Resultado do `pytest`.
6. Resultado do `python manage.py check` e outras validações.
7. Pendências, falhas preexistentes ou comandos que não puderam ser executados.

Se uma regra deste documento conflitar com uma solicitação, não a ignore em silêncio: explique o conflito e peça confirmação antes de qualquer ação destrutiva ou irreversível.

D2: leitura pública de posts, tags e comentários; escrita exige login.