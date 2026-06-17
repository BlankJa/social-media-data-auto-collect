"""冒烟测试：强制 typer 构建所有命令。

pytest 平时只 import cli、不调 app()，所以命令注册层的错误（比如把内部
帮助函数错挂 @app.command()、或命令参数用了非 CLI 类型）测不出来——
曾因此让 `RuntimeError: Type not yet supported: Account` 漏进已 push 的
commit。跑一次 --help 即可触发 click/typer 对每个命令的参数解析。"""

from typer.testing import CliRunner

from cli import app

runner = CliRunner()


def test_root_help_builds():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("collect", "render", "status", "account"):
        assert cmd in result.output
    # 内部帮助函数不该被注册成命令
    assert "select-render-posts" not in result.output


def test_each_command_help_builds():
    for cmd in ("collect", "render", "status"):
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0, f"{cmd} --help 构建失败：{result.output}"


def test_account_subcommands_build():
    result = runner.invoke(app, ["account", "--help"])
    assert result.exit_code == 0
    for sub in ("list", "add", "remove", "import", "template"):
        assert sub in result.output
