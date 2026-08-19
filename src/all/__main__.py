"""Allow running as: python -m modbus_cli"""
from .main import main
import sys

sys.exit(main())
