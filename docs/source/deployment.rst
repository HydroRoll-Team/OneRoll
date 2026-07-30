Documentation deployment
========================

The production documentation at https://oneroll.hydroroll.team/ is a strict
Sphinx HTML build using the Furo theme.  Cloudflare Workers Static Assets serves
the generated files; ``wrangler.docs.jsonc`` is the source of truth for the
Worker name, asset directory, and domain route.

Local workflow
--------------

Install the pinned Wrangler release once, then use the repository scripts:

.. code-block:: console

   npm ci
   npm run docs:dev
   npm run docs:build
   npm run docs:deploy:dry-run

``docs:build`` cleans the previous output, keeps Sphinx doctrees outside the
public asset directory, treats warnings as errors, and writes deployable HTML to
``docs/_build/html``.  An authenticated maintainer may publish the same target
from a workstation with ``npm run docs:deploy``.

Automatic production deployment
--------------------------------

``.github/workflows/docs.yml`` runs for pull requests that affect documentation
inputs and for matching pushes to ``main``.  The production path is deliberately
split:

#. the reusable repository quality gate succeeds;
#. Sphinx builds and verifies one Furo artifact;
#. pull requests stop without receiving Cloudflare credentials; and
#. a ``main`` push downloads that exact artifact and deploys it through the
   protected ``docs-production`` GitHub environment.

The workflow watches ``docs/``, package/version inputs used by Sphinx, the
Python source imported by autodoc, and the deployment configuration itself.
Unrelated repository changes do not trigger an extra documentation deployment.

Repository prerequisites
------------------------

Repository administrators configure these values outside source control:

``CLOUDFLARE_ACCOUNT_ID``
   A GitHub Actions repository variable containing the Cloudflare account ID.

``CLOUDFLARE_API_TOKEN``
   A secret in the ``docs-production`` GitHub environment.  Create it from
   Cloudflare's **Edit Cloudflare Workers** token template and restrict its
   account and zone resources to the account that owns ``hydroroll.team``.

Never commit the token or copy a local Wrangler OAuth credential into GitHub.
The route declaration binds every path below ``oneroll.hydroroll.team`` to the
static-assets Worker.  It relies on the existing proxied DNS record as a route
anchor; do not disable its Cloudflare proxy or delete it without first migrating
the Wrangler configuration to a Workers Custom Domain.

Operational checks
------------------

After a production deployment, verify the Worker and public domain:

.. code-block:: console

   wrangler deployments list --name oneroll-docs
   curl --fail --show-error --location https://oneroll.hydroroll.team/
   curl --fail --show-error --location https://oneroll.hydroroll.team/language

Use ``wrangler versions list --name oneroll-docs`` to identify an earlier
version and ``wrangler rollback --name oneroll-docs <version-id>`` when a
validated rollback is required.
