# docker-zerotier-moon
<a href="https://github.com/wxx9248/docker-zerotier-moon/actions">
    <img
        src="https://img.shields.io/github/actions/workflow/status/wxx9248/docker-zerotier-moon/build.yaml?branch=master"
        alt="GitHub Actions Status" />
</a>
<img src="https://img.shields.io/docker/v/zerotier/zerotier?sort=semver" alt="Image Version" />

## Credits
* [rwv/docker-zerotier-moon](https://github.com/rwv/docker-zerotier-moon)
* [zerotier/zerotier](https://github.com/zerotier/ZeroTierOne)

## What's different?
* Changed based image to `zerotier-zerotier`.
    * Alpine seemed to drop support for ZeroTier in the latest branch,
    as for now, [v3.18](https://pkgs.alpinelinux.org/packages?name=zerotier-one&branch=v3.18),
    so I decided to create a moon server image from the official ZeroTier image,
    which is bigger (based on Debian) but is guaranteed to keep up with the latest ZeroTier release.
* Re-wrote `entrypoint` file with Python
    * There is a reference to the Bash implementation in rwv's repository.
    * I just don't want to replace JSON fields with `sed` - it can get messy.
* Moons can join networks now
    * I kept the feature from the official image.
    * With a few environment variables, you can specify the identity of the moon server,
    as well as networks the moon server should be in.

## Usage
```
Usage: docker run [DOCKER_OPTIONS] ghcr.io/wxx9248/zerotier-moon:master [OPTIONS]...
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
```

## Quick Start (from rwv's repo)
### Start a container
```
docker run --name zerotier-moon -d --restart always -p 9993:9993/udp -v ~/somewhere:/var/lib/zerotier-one ghcr.io/wxx9248/zerotier-moon:master -4 1.2.3.4
```
Replace `1.2.3.4` with your moon's IPv4 address and replace `~/somewhere` with where you would like to store your configuration.

### Show ZeroTier moon ID
```
docker logs zerotier-moon
```

## Docker Compose
### Compose file
`docker-compose.yml` example:
``` YAML
services:
  zerotier-moon:
    image: ghcr.io/wxx9248/zerotier-moon:master
    container_name: "zerotier-moon"
    restart: always
    ports:
      - "9993:9993/udp"
    volumes:
      - ./config:/var/lib/zerotier-one
    command: ["-4", "1.2.3.4"]
```
Replace `1.2.3.4` with your moon's IPv4 address.

### Show ZeroTier moon ID
``` bash
docker-compose logs
```

## Advanced usage
### Manage ZeroTier
```
docker exec zerotier-moon zerotier-cli
```

### Mount ZeroTier conf folder
```
docker run --name zerotier-moon -d -p 9993:9993/udp -v ~/somewhere:/var/lib/zerotier-one ghcr.io/wxx9248/zerotier-moon:master -4 1.2.3.4
```
When creating a new container without mounting ZeroTier conf folder, a new moon ID will be generated.
This command will mount `~/somewhere` to `/var/lib/zerotier-one` inside the container, allowing your ZeroTier moon to presist the same moon ID. If you don't do this, when you start a new container, a new moon ID will be generated.

### IPv6 support
```
docker run --name zerotier-moon -d -p 9993:9993/udp ghcr.io/wxx9248/zerotier-moon:master -4 1.2.3.4 -6 2001:abcd:abcd::1
```
Replace `1.2.3.4`, `2001:abcd:abcd::1` with your moon's IP. You can remove `-4` option in pure IPv6 environment.

### Custom port
```
docker run --name zerotier-moon -d -p 9994:9993/udp ghcr.io/wxx9248/zerotier-moon:master -4 1.2.3.4 -p 9994
```
Replace 9994 with your own custom port for ZeroTier moon.

### Network privilege
If you encounter issue: `ERROR: unable to configure virtual network port: could not open TUN/TAP device: No such file or directory`, please add `--cap-add=NET_ADMIN --cap-add=SYS_ADMIN --device=/dev/net/tun` args. Similar to this:

```
docker run --cap-add=NET_ADMIN --cap-add=SYS_ADMIN --device=/dev/net/tun --name zerotier-moon -d --restart always -p 9993:9993/udp ghcr.io/wxx9248/zerotier-moon:master -4 1.2.3.4
```
Solution provided by [Jonnyan404's Fork](https://github.com/Jonnyan404/docker-zerotier-moon).
See Also [Issue #1](https://github.com/rwv/docker-zerotier-moon/issues/1).

### Multi-arch support
This image supports `linux/amd64`, `linux/386`, `linux/arm64`, `linux/arm/v5`, `linux/arm/v7`, `linux/ppc64le`, `linux/s390x` and `linux/mips64le`.
