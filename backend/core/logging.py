import logging
import sys

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

logging.basicConfig(level=logging.INFO, format=_FORMAT, handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger("hcp_crm")
db_logger = logging.getLogger("hcp_crm.db")
llm_logger = logging.getLogger("hcp_crm.llm")
tool_logger = logging.getLogger("hcp_crm.tools")
stream_logger = logging.getLogger("hcp_crm.stream")
error_logger = logging.getLogger("hcp_crm.error")
