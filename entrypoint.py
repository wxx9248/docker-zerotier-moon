#!/usr/bin/env python3
import os
import sys
import typing
import json
import getopt
import socket
import subprocess
import time
import traceback

DEFAULT_PORT = "9993"
EXECUTABLE_DIR_PATH = "/usr/sbin"
CONFIG_DIR_PATH = "/var/lib/zerotier-one"


def main(argc: int, argv: typing.List):
    option_dict, _ = parse_command_line(argv)
    if len(option_dict) == 0:
        print_usage(argv[0], shorten=True)
        return 0
    if "help" in option_dict:
        print_usage(argv[0])
        return 0

    envvar_dict = parse_environment_variables()

    config_dict = {**envvar_dict, **option_dict}
    validate_config(config_dict)

    preinit_config(config_dict)
    init()
    preinit_moon(config_dict)
    start()

    return 0


def parse_command_line(argv: typing.List) \
        -> typing.Tuple[typing.Dict[str, str], str]:
    option_dict = {}

    try:
        options, arguments = getopt.getopt(
            argv[1:],
            "h4:6:p:",
            ["help", "ipv4=", "ipv6=", "port="]
        )
    except getopt.GetoptError:
        raise

    for (option, value) in options:
        if option in ("-h", "--help"):
            option_dict["help"] = True
        elif option in ("-4", "--ipv4"):
            option_dict["ipv4"] = value
        elif option in ("-6", "--ipv6"):
            option_dict["ipv6"] = value
        elif option in ("-p", "--port"):
            option_dict["port"] = value
        else:
            raise ValueError(f"Unknown option: {option}")

    return option_dict, arguments


def parse_environment_variables() \
        -> typing.Dict[str, typing.Union[str, typing.List[str]]]:
    arrayed = [
        "join_networks"
    ]

    envvar_dict = {
        key[9:].lower(): value
        for key, value in os.environ.items()
        if key.startswith("ZEROTIER_")
    }

    # Process space-seperated envvars
    for names in arrayed:
        try:
            envvar_dict[names] = envvar_dict[names].split()
        except KeyError:
            pass

    return envvar_dict


def validate_config(config_dict: typing.Dict[str, str]):
    # Verify presence of necessary entries
    if "ipv4" not in config_dict and "ipv6" not in config_dict:
        raise ValueError(
            "Must specify either an IPv4 address or an IPv6 address, or both"
        )

    # Verify if arguments are well-formed
    try:
        ipv4 = config_dict["ipv4"]
        if not is_valid_address(socket.AF_INET, ipv4):
            raise ValueError(f"{ipv4} is not a valid IPv4 address")
    except KeyError:
        pass

    try:
        ipv6 = config_dict["ipv6"]
        if not is_valid_address(socket.AF_INET6, ipv6):
            raise ValueError(f"{ipv6} is not a valid IPv6 address")
    except KeyError:
        pass

    try:
        port = config_dict["port"]
        if not 0 < int(port) < 65536:
            raise ValueError(f"{port} is not a valid port number")
    except KeyError:
        print_info(f"Port not specified, using default port {DEFAULT_PORT}")
        config_dict["port"] = DEFAULT_PORT


def preinit_config(config_dict: typing.Dict[str, str]):
    create_text_file(
        CONFIG_DIR_PATH,
        "zerotier-one.port",
        0o600,
        config_dict["port"]
    )

    try:
        create_text_file(
            CONFIG_DIR_PATH,
            "authtoken.secret",
            0o600,
            config_dict["api_secret"]
        )
    except KeyError:
        print_info("No API secret specified")

    try:
        create_text_file(
            CONFIG_DIR_PATH,
            "identity.public",
            0o644,
            config_dict["identity_public"]
        )
    except KeyError:
        print_info("No public key specified")

    try:
        create_text_file(
            CONFIG_DIR_PATH,
            "identity.secret",
            0o600,
            config_dict["identity_secret"]
        )
    except KeyError:
        print_info("No private key specified")

    try:
        for network_id in config_dict["join_networks"]:
            print_info(f"Configuring network {network_id[:4]}")
            create_text_file(
                os.path.join(CONFIG_DIR_PATH, "networks.d"),
                f"{network_id}.conf",
                0o644,
                ""
            )
    except KeyError:
        print_info("No networks to configure")


def init():
    print_info("Starting ZeroTier daemon to create config files")
    process = subprocess.Popen(
        [
            os.path.join(EXECUTABLE_DIR_PATH, "zerotier-one"),
            "-U"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    while True:
        time.sleep(1)
        if process.poll() is not None:
            e = RuntimeError(
                f"`zerotier-one` terminated prematurely ({process.returncode})"
            )
            e.console_log = process.stdout
            raise e
        if os.path.isfile(os.path.join(CONFIG_DIR_PATH, "zerotier-one.pid")):
            print_info("Config generated")
            break
        print_info("Waiting for ZeroTier daemon...")

    print_info("Terminating ZeroTier daemon")
    process.terminate()
    process.wait()


def preinit_moon(config_dict: typing.Dict[str, str]):
    process = subprocess.Popen(
        [
            os.path.join(EXECUTABLE_DIR_PATH, "zerotier-idtool"),
            "initmoon",
            os.path.join(CONFIG_DIR_PATH, "identity.public")
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    process.wait()
    if process.returncode != 0:
        e = RuntimeError(
            f"`zerotier-idtool initmoon` failed ({process.returncode})"
        )
        e.console_log = process.stdout
        raise e

    moon_config = json.load(process.stdout)
    port = config_dict["port"]

    for root in moon_config["roots"]:
        if "ipv4" in config_dict:
            ipv4 = config_dict["ipv4"]
            root["stableEndpoints"].append(f"{ipv4}/{port}")
        if "ipv6" in config_dict:
            ipv6 = config_dict["ipv6"]
            root["stableEndpoints"].append(f"{ipv6}/{port}")

    create_text_file(
        os.path.join(CONFIG_DIR_PATH),
        "moon.json",
        0o644,
        json.dumps(moon_config)
    )

    os.makedirs(os.path.join(CONFIG_DIR_PATH, "moons.d"), exist_ok=True)
    process = subprocess.Popen(
        [
            os.path.join(EXECUTABLE_DIR_PATH, "zerotier-idtool"),
            "genmoon",
            os.path.join(CONFIG_DIR_PATH, "moon.json")
        ],
        cwd=os.path.join(CONFIG_DIR_PATH, "moons.d"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    process.wait()
    if process.returncode != 0:
        e = RuntimeError(
            f"`zerotier-idtool genmoon` failed ({process.returncode})"
        )
        e.console_log = process.stdout
        raise e


def start():
    process = subprocess.Popen(
        [os.path.join(EXECUTABLE_DIR_PATH, "zerotier-one"), "-U"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    try:
        with open(os.path.join(CONFIG_DIR_PATH, "identity.public")) as f:
            moon_id = f.read().split(":")[0]
            print_info(f"Moon ID: {moon_id}")
            print_info("Use the following command to orbit the moon:")
            print_info(f"\tzerotier-cli orbit {moon_id} {moon_id}")

        while process.poll() is None:
            line = process.stdout.readline()
            if line == "":
                break
            print_info(f"[ZeroTier] {line.rstrip()}")
    finally:
        process.terminate()
        print_info("Waiting daemon to quit...")
        process.wait()


def create_text_file(
    dir_path: str,
    file_name: str,
    permission: int,
    content: str
):
    os.makedirs(dir_path, exist_ok=True)
    with open(os.path.join(dir_path, file_name), "w") as f:
        f.write(content)
    os.chmod(os.path.join(dir_path, file_name), permission)


def is_valid_address(family: socket.AddressFamily, address: str):
    try:
        socket.inet_pton(family, address)
        return True
    except socket.error:
        return False


def print_usage(program_name: str, shorten: bool = False):
    short_help_text = f"Usage {program_name} [-h46p]"
    long_help_text = f"""Usage: {program_name} [OPTIONS]...
Available options:
    -h, --help
        Display help text
    -4, --ipv4 <IPV4_ADDRESS>
        Specify a public IPv4 address
    -6, --ipv6 <IPV6_ADDRESS>
        Specify a public IPv6 address
    -p, --port <PORT_NUMBER>
        Specify a UDP port that ZeroTier will listen to

Note: must specify at least one type of address.

Optional environment variables:
    ZEROTIER_API_SECRET
        Specify an API secret
        Will overwrite `authtoken.secret` file
        Leave empty for automatic generation
    ZEROTIER_IDENTITY_PUBLIC
        Specify a public key for identification
        Will overwrite `identity.public` file
        Leave empty for automatic generation
    ZEROTIER_IDENTITY_SECRET
        Specify a private key for identification
        Will overwrite `identity.public` file
        Leave empty for automatic generation
    ZEROTIER_JOIN_NETWORKS
        Specify a list of network IDs, seperated by spaces,
        that will be joined upon initialization
"""
    if shorten:
        print(short_help_text, file=sys.stderr)
        return
    print(long_help_text, end="", file=sys.stderr)


def print_info(message: str):
    print(f"[i] {message}", file=sys.stderr)


def print_error(message: str):
    print(f"[-] {message}", file=sys.stderr)


if __name__ == "__main__":
    try:
        exit(main(len(sys.argv), sys.argv))
    except Exception as e:
        for line in traceback.format_exc().splitlines(keepends=False):
            print_error(line)

        if not hasattr(e, "console_log"):
            exit(1)

        print_error("Console log:")
        while True:
            line = e.console_log.readline()
            if line == "":
                break
            print_error(line.rstrip())
