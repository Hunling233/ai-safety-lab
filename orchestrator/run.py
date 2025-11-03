from adapters.verimedia_adapter import VeriMediaAdapter
ADAPTERS = {
    "verimedia": lambda params: VeriMediaAdapter(
        base_url=params.get("base_url","http://127.0.0.1:5004"),
        timeout=int(params.get("timeout",120))
    )
}
