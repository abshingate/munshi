# Tally Cloud Workstation

**An on-demand Windows computer on AWS for Indian accounting and compliance —
TallyPrime, GST, TDS, PF, ESIC, MCA — that costs almost nothing while switched
off, loses nothing between sessions, and can be operated by someone with zero
technical knowledge.**

[Get the code on GitHub](https://github.com/abshingate/tally-cloud-workstation){: .btn }

## Why this exists

Small firms and independent accountants need Tally and a dozen government
portals **once or twice a month** — but a dedicated PC (or an always-on cloud
VM) costs real money the other 28 days. This project gives you:

| | |
|---|---|
| 💰 **~₹900–1,000/month** | vs ₹8,000+ for an always-on cloud Windows VM |
| 🌐 **Works in a browser** | Amazon DCV desktop; RDP and AWS Fleet Manager as fallbacks |
| 🔐 **DSC token support** | Sign filings with the USB token plugged into your local machine |
| 💾 **Data can't be lost** | Persistent encrypted disk, nightly snapshots, termination protection |
| 🛡️ **Cost can't run away** | Idle auto-stop, budget alarms, email alerts |
| 🧓 **Grandparent-proof** | Numbered double-click buttons, plain-language guide, self-diagnosing health checks |

## Three ways to deploy

1. **Mac, one double-click** — button `0 - First Time Setup` installs its own
   tooling and walks you through it.
2. **Any browser, zero installs** — AWS CloudShell: upload the zip, paste two
   lines. Done.
3. **Terraform users** — `cp terraform.tfvars.example terraform.tfvars`,
   `terraform init && terraform apply`.

## Documentation

- [README](https://github.com/abshingate/tally-cloud-workstation#readme) —
  architecture, deployment, operations (for the technical person)
- [User Guide](https://github.com/abshingate/tally-cloud-workstation/blob/main/USER-GUIDE.md) —
  plain-language manual (for the accountant)
- [Contributing](https://github.com/abshingate/tally-cloud-workstation/blob/main/CONTRIBUTING.md) ·
  [Security policy](https://github.com/abshingate/tally-cloud-workstation/blob/main/SECURITY.md) ·
  [Changelog](https://github.com/abshingate/tally-cloud-workstation/blob/main/CHANGELOG.md)

## License

Open source under the [Apache License 2.0](https://github.com/abshingate/tally-cloud-workstation/blob/main/LICENSE).
