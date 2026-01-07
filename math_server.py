from mcp.server.fastmcp import FastMCP

app = FastMCP(name="math", port=8001)

@app.tool()
def multiply(a: float, b: float) -> dict:
    """
    Multiply two numbers.
    """
    return {
        "a": a,
        "b": b,
        "result": a * b
    }

if __name__ == "__main__":
    app.run(transport="streamable-http")
