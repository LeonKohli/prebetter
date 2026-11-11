# Prebetter backend

A read-only FastAPI adapter on the IDS alerts stored in OpenSearch. It serves the alert list, address-pair groups, alert detail, a change stream, a timeline, and the reference lists for the filters. It verifies Better Auth JWTs through JWKS. User and session management belong to the [Nuxt frontend](../frontend/README.md).

## Set up

From this directory:

```sh
uv sync --locked
cp .env.example .env
```

Fill in the settings in `.env`. `BETTER_AUTH_URL` must match the frontend origin because it defines the expected JWT issuer, audience, and JWKS location.

| Setting | Meaning |
|---|---|
| `OPENSEARCH_URL` | Base URL of the node, for example `https://opensearch.example.org:9200`. An `https` URL enables TLS with certificate verification against the default trust store. |
| `OPENSEARCH_INDEX` | Index pattern with the daily event indices, for example `ids-events-*`. |
| `OPENSEARCH_REQUEST_INDEX` | Index pattern with the daily request-line indices, for example `ids-requests-*`. The ingest pipeline stores one companion document per HTTP alert there; the alert detail shows its request line. Alerts without a companion show none. |
| `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD` | Optional basic-authentication credentials. Leave both unset for a node without the security plugin. |
| `BETTER_AUTH_URL` | Frontend origin; JWT issuer, audience, and JWKS source. |
| `ENVIRONMENT`, `LOG_LEVEL`, `BACKEND_CORS_ORIGINS` | Runtime settings. |

Start the API:

```sh
uv run fastapi dev
```

The frontend must be reachable at `BETTER_AUTH_URL` when the API fetches signing keys.

### Local node with sample data

`compose.opensearch.yml` in the repository root starts a single OpenSearch 3.9 node without security on `127.0.0.1:9200`.

```sh
docker compose -f ../compose.opensearch.yml up -d
OPENSEARCH_URL=http://127.0.0.1:9200
OPENSEARCH_INDEX=ids-events-*
OPENSEARCH_REQUEST_INDEX=ids-requests-*
```

Set those values in `.env`, then load twelve synthetic events into two daily indices, created from the production index template in `tests/index_template.json`, and the request-line companion of one of them in a daily index from `tests/requests_template.json`:

```sh
uv run python -m tests.seed
```

The command refuses to run when `OPENSEARCH_URL` is not `localhost` or `127.0.0.1`. The events are dated relative to the current hour, so a repeated run within the same hour changes nothing.

## API reference

All routes live under `/api/v1` and require a Bearer token. The [OpenAPI documentation](http://localhost:8000/api/v1/docs) lists every parameter and response.

| Path | Purpose |
|---|---|
| `GET /alerts` | Paged, filtered, sorted alert list. |
| `GET /alerts/groups` | Alerts grouped by (source, target) address pair, with counts per rule name. |
| `GET /alerts/{alert_id}` | One alert with typed fields, the Snort packet fields, the captured payload (base64, when the sensor logs it), the client address from `X-Forwarded-For`, and the complete stored document. `alert_id` is the 64-character event id. |
| `GET /alerts/stream` | Server-sent events that tell the UI to refetch. |
| `GET /statistics/timeline` | Alert counts per minute, hour, day, or week. |
| `GET /reference/severities`, `/servers`, `/classifications` | Values for the filter inputs. |

`GET /health` needs no token. It reports `opensearch: true` when a document count on the index pattern succeeds, and `status: unhealthy` otherwise. When OpenSearch is unreachable, every other route answers 503.

Filters shared by the list, groups, and timeline: `start_date`, `end_date`, `severity` (`high`, `medium`, `low`, `info`, comma-separated), `classification` (rule names), `server` (sensor names), `source_ip` and `target_ip` (an address, a CIDR network, or a partial IPv4 prefix such as `10.128`), and `require_ips` (default `true`). Response field names such as `source_ipv4`, `classification_text`, and `analyzer` are the names the frontend uses; `app/opensearch/documents.py` maps them to the document fields.

## How the adapter queries OpenSearch

- **Filters** go into the `bool.filter` context, so nothing is scored. A `term` query on an `ip` field accepts a CIDR network, which covers address, network, and prefix filters.
- **The list** uses `from`/`size` paging with an exact `track_total_hits` and ends every sort with `event.id`, so pages never overlap. `index.max_result_window` limits paging to the first 10,000 results; a request beyond that answers 422. Sorting by severity inverts the direction, because Snort priority 1 is the most severe.
- **Pair groups and the reference lists** must be exact, so they use `composite` aggregations that follow `after_key` to the end instead of a `terms` top-N. The pair list is sorted in Python and sliced, then one more composite fetches the rule names for the pairs on the page. More than 50,000 pairs answer 422.
- **The timeline** is a `date_histogram` in UTC that omits empty buckets. Weeks start on Monday.
- **The stream** polls `_count` on the index pattern every 5 seconds and sends `event: alerts` when the count has grown. A count also catches alerts that arrive late with an old event time, which a timestamp cursor would miss.
- **Severity** maps Snort priority 0 and 1 to `high`, 2 to `medium`, 3 to `low`, and 4 and above to `info`.

### Required OpenSearch permissions

The adapter calls only `_search` and `_count`. Index-level `read` on the `OPENSEARCH_INDEX` and `OPENSEARCH_REQUEST_INDEX` patterns is enough. It needs no cluster permissions and never writes.

## Tests

The tests run against a real OpenSearch node, because the strict index mapping and the `ip` and `keyword` field types decide what the queries return.

```sh
docker compose -f ../compose.opensearch.yml up -d
uv run ruff check .
uv run pytest
docker compose -f ../compose.opensearch.yml down
```

`tests/conftest.py` reads `OPENSEARCH_URL`, `OPENSEARCH_INDEX` and `OPENSEARCH_REQUEST_INDEX` from the environment, or from `.env.test` (not committed). Exported variables take precedence. A minimal `.env.test` for the local node:

```
OPENSEARCH_URL=http://127.0.0.1:9200
OPENSEARCH_INDEX=prebetter-test-events-*
OPENSEARCH_REQUEST_INDEX=prebetter-test-requests-*
BETTER_AUTH_URL=http://localhost:3000
ENVIRONMENT=test
LOG_LEVEL=WARNING
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
```

The suite refuses to run unless both patterns start with `prebetter-test-`. It creates the daily indices from `tests/index_template.json` and `tests/requests_template.json`, indexes the events and request companions from `tests/seed.py` with `refresh`, and deletes the indices afterwards.

The [CI workflow](../.github/workflows/checks.yml) runs the same suite against an OpenSearch service container.
