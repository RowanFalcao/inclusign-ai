# Diretrizes de Contribuição — IncluSign AI

Obrigado pelo interesse em contribuir com a democratização da educação inclusiva e a acessibilidade em Libras!

## 1. Fluxo de Desenvolvimento Local

1. Realize um Fork do repositório.
2. Clone o repositório em sua máquina:
   ```bash
   git clone https://github.com/seu-usuario/inclusign-ai.git
   cd inclusign-ai
   ```
3. Crie um ambiente virtual e instale as dependências de desenvolvimento:
   ```bash
   python -m venv .venv
   # Linux/macOS:
   source .venv/bin/activate
   # Windows:
   .\.venv\Scripts\Activate.ps1

   pip install -r requirements-dev.txt
   ```
4. Instale os hooks do pre-commit:
   ```bash
   pre-commit install
   ```

## 2. Padrões de Código e Verificação Obrigatória

Antes de abrir um Pull Request, certifique-se de que todas as validações passam localmente:

- **Linting e Formatação:**
  ```bash
  ruff check .
  ruff format .
  ```
- **Checagem de Tipos:**
  ```bash
  mypy app.py config.py agents/ services/
  ```
- **Suíte de Testes:**
  ```bash
  pytest tests -v
  ```

## 3. Padrão de Commits

Adotamos rigorosamente o **Conventional Commits**:
- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Alterações na documentação
- `test:` Inclusão ou melhoria de testes
- `refactor:` Alterações de código que não mudam a funcionalidade

