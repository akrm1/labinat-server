from typing import Union
from pathlib import Path
import importlib.util
import inspect
from types import ModuleType

class RuntimeModule():
    def __init__(self, module_name: str, path: Union[str, Path]):
        self.module_name : str = module_name
        self.path : Path = Path(path)
        
        spec = importlib.util.spec_from_file_location(self.module_name, self.path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.__module : ModuleType = module

    def __str__(self):
        return f"<\'{self.module_name}\' RuntimeModule> ({self.path})"

    def __repr__(self):
        return f"<\'{self.module_name}\' RuntimeModule> ({self.path})"

    def __getitem__(self, key: str):
        try:
            return getattr(self.__module, key)
        except Exception as e:
            raise RuntimeError(f"Identifier \'{key}\' not found") from e
    
    def validate_function(self, function_name: str, signature: dict[str, dict]):
        module_function = self[function_name]

        function_params = inspect.signature(module_function).parameters
        for sig_param_name, sig_param in signature.items():
            func_param = function_params.get(sig_param_name, None)
            if func_param is None:
                raise RuntimeError(f"Function parameter \'{sig_param_name}\' is not defined on \'{function_name}\' function.")

            sig_param_type = sig_param['type']
            func_param_type = func_param.annotation
            if func_param_type != sig_param_type:
                raise RuntimeError(f"Function parameter \'{sig_param_name}\' is of type \'{func_param_type}\' but expected type \'{sig_param_type}\'")
        

