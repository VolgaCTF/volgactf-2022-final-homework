# VolgaCTF 2022 Final Homework

This repo contains all the checkers from `VolgaCTF 2022 Final` along with a game-simulating script.

Could be useful to do your _homework_.

## Build

```bash
$ docker build -t volgactf2022/homework-image .
```

## Run

```bash
$ docker run \
    -e TEAM_IP=<host-ip> \
    -e ROUND_DURATION=10 \
    --rm \
    volgactf2022/homework-image
```

## Optional environment variables

### Simulation-related variables
| Var name                    | Description                                          |    Default value    |
|-----------------------------|------------------------------------------------------|:-------------------:|
| `ROUND_DURATION`            | Round duration (time between two consecutive PUSHes) |       30 sec        |
| `SKIP_EDITOR`               | Skip `Editor` service                                |        False        |
| `SKIP_AESTHETIC`            | Skip `Aesthetic` service                             |        False        |
| `SKIP_MYBLOG`               | Skip `MyBlog` service                                |        False        |
| `SKIP_JINNICE`              | Skip `Jinnice` service                               |        False        |
| `PULL_COUNT`                | Number of PULLs for each round                       |          5          |
| `PRINT_STATS_EVERY_N_ROUND` | Output stats frequency                               |          1          |
| `PRINT_STATS_SINGLE_COLUMN` | Output stats in a single column                      | False (two columns) |

### Checkers' variables
| Var name                       | Description                              | Default value |
|--------------------------------|------------------------------------------|:-------------:|
| `EDITOR_PORT`                  | `Editor` service port                    |     8080      |
| `EDITOR_TIMEOUT`               | `Editor` service connection timeout      |      30       |
| `EDITOR_N_MAX_IMAGES_PER_PUSH` | Max number of images to PUSH to `Editor` |       3       |
| `AESTHETIC_PORT`               | `Aesthetic` service port                 |     8777      |
| `AESTHETIC_TIMEOUT`            | `Aesthetic` service connection timeout   |      15       |
| `MYBLOG_PORT`                  | `MyBlog` service port                    |     13377     |
| `MYBLOG_TIMEOUT`               | `MyBlog` service connection timeout      |      20       |
| `JINNICE_PORT`                 | `Jinnice` service port                   |     8888      |
| `JINNICE_TIMEOUT`              | `Jinnice` service connection timeout     |      30       |

### Example with more options
Below is an example usage which assumes that only `Editor` and `MyBlog` services are spawned, 
`Editor`'s port is `18080`, and `MyBlog` checker's connection timeout is increased (e.g. for debugging purposes): 
```bash
$ docker run \
    -e TEAM_IP=<host-ip> \
    -e ROUND_DURATION=10 \
    -e SKIP_AESTHETIC= \
    -e SKIP_JINNICE= \
    -e EDITOR_PORT=18080 \
    -e MYBLOG_TIMEOUT=1800 \
    --rm \
    volgactf2022/homework-image
```

## License

MIT @ [VolgaCTF](https://github.com/VolgaCTF)
