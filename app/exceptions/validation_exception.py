class ValidationException(Exception):
    """
    Exceção para erros de validação de dados ou regras de negócio.
    Deve resultar em erro 4xx no controller.
    """
    pass