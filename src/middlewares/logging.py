import coloredlogs, logging

logging.basicConfig()
logger = logging.getLogger(name="TGDex Discussion")
logger.propagate = False  # Prevent logs from propagating to parent logger

# Configure colored logs
coloredlogs.install(
    level="DEBUG",  # Set the default logging level to DEBUG
    logger=logger,
    fmt="[%(name)s] %(asctime)s %(funcName)s %(lineno)-3d %(message)s",
    level_styles=dict(
        debug=dict(color="white"),
        info=dict(color="cyan", bold=True, bright=True),
        warning=dict(color="yellow", bold=True, bright=True),
        error=dict(color="red", bold=True, bright=True),
        critical=dict(color="white", bold=True, background="red"),
    ),
    field_styles=dict(
        name=dict(color="yellow", bold=True, bright=True, italic=True),
        asctime=dict(color="green", bold=True, bright=True),
        funcName=dict(color="magenta", bold=True, bright=True),
        lineno=dict(color="red", bold=True, bright=True, italic=True),
        message=dict(color="blue", bold=True, bright=True),
    ),
)
