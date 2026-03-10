# Rule Engine Design

## Objective

Provide deterministic translation of CIS benchmark controls into Intune
configuration mappings.

------------------------------------------------------------------------

## Rule engine overview

Rules inspect: - title - GPO path - registry path - recommended value

Rules produce an `IntuneMapping` object.

------------------------------------------------------------------------

## Rule interface

Each rule implements:

matches(control)\
apply(control)

Example:

class MappingRule: def matches(self, control): pass

    def apply(self, control):
        pass

------------------------------------------------------------------------

## Example rule

class ConsumerExperienceRule(MappingRule):

    def matches(self, control):
        return "consumer experiences" in control.title.lower()

    def apply(self, control):
        return IntuneMapping(
            implementation_type="settings_catalog",
            setting_name="Turn off Microsoft consumer experiences",
            value="enabled"
        )

------------------------------------------------------------------------

## Rule categories

  rule category            purpose
  ------------------------ --------------------
  Defender rules           antivirus settings
  Firewall rules           firewall policies
  BitLocker rules          encryption
  Settings catalog rules   Windows policies
  Browser rules            Edge / Chrome

------------------------------------------------------------------------

## Rule priority

1.  Endpoint Security rules\
2.  Settings Catalog rules\
3.  Administrative template rules\
4.  OMA URI fallback\
5.  Manual review

------------------------------------------------------------------------

## Resolver example

for control in controls: for rule in rules: if rule.matches(control):
return rule.apply(control)

------------------------------------------------------------------------

## Output example

{ "cis_id": "18.9.85.1.1", "implementation_type": "settings_catalog",
"setting_name": "Turn off Microsoft consumer experiences", "value":
"enabled", "confidence": 0.95 }
