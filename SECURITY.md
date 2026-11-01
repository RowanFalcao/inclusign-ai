# Política de Segurança — IncluSign AI

## Relato Responsável de Vulnerabilidades

A segurança e a privacidade dos dados pedagógicos de estudantes e professores são prioritárias. Se você identificar qualquer vulnerabilidade de segurança, por favor siga este protocolo:

1. **Não abra uma Issue pública** para reportar vulnerabilidades de segurança exploráveis.
2. Envie um e-mail com os detalhes técnicos e passos de reprodução para os mantenedores do projeto.
3. A equipe responderá em até 48 horas confirmando o recebimento e avaliando o plano de mitigação.

## Boas Práticas Implementadas

- Execução 100% offline via modelos locais (zero vazamento de dados confidenciais para servidores em nuvem).
- Contêiner Docker executado sob usuário não-privilegiado (`appuser`).
- Sanitização de caminhos de arquivo para prevenção de *Path Traversal*.
- Checagem automatizada de vulnerabilidades em dependências via CI/CD.

