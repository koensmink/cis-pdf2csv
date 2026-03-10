from __future__ import annotations

from abc import ABC, abstractmethod

from .models import IntuneMapping, MappingInputControl


class MappingRule(ABC):
    rule_id: str

    @abstractmethod
    def matches(self, control: MappingInputControl) -> bool:
        raise NotImplementedError

    @abstractmethod
    def apply(self, control: MappingInputControl) -> IntuneMapping:
        raise NotImplementedError


class ConsumerExperienceRule(MappingRule):
    rule_id = "settings_catalog.consumer_experience"

    def matches(self, control: MappingInputControl) -> bool:
        return "consumer experiences" in control.title.lower()

    def apply(self, control: MappingInputControl) -> IntuneMapping:
        return IntuneMapping(
            cis_id=control.control_id,
            title=control.title,
            implementation_type="settings_catalog",
            intune_area="Windows OS Hardening",
            setting_name="Turn off Microsoft consumer experiences",
            value="Enabled",
            confidence=0.95,
            rule_id=self.rule_id,
        )


class DefenderRule(MappingRule):
    rule_id = "endpoint_security.defender"

    def matches(self, control: MappingInputControl) -> bool:
        t = control.title.lower()
        return "defender" in t or "microsoft defender" in t

    def apply(self, control: MappingInputControl) -> IntuneMapping:
        return IntuneMapping(
            cis_id=control.control_id,
            title=control.title,
            implementation_type="endpoint_security",
            intune_area="Defender Security",
            setting_name="Microsoft Defender Antivirus",
            value=control.default_value or "Use CIS recommended value",
            confidence=0.50,
            rule_id=self.rule_id,
        )


class FirewallRule(MappingRule):
    rule_id = "endpoint_security.firewall"

    def matches(self, control: MappingInputControl) -> bool:
        return "firewall" in control.title.lower()

    def apply(self, control: MappingInputControl) -> IntuneMapping:
        return IntuneMapping(
            cis_id=control.control_id,
            title=control.title,
            implementation_type="endpoint_security",
            intune_area="Firewall",
            setting_name="Microsoft Defender Firewall",
            value=control.default_value or "Use CIS recommended value",
            confidence=0.50,
            rule_id=self.rule_id,
        )


class BitLockerRule(MappingRule):
    rule_id = "endpoint_security.bitlocker"

    def matches(self, control: MappingInputControl) -> bool:
        return "bitlocker" in control.title.lower()

    def apply(self, control: MappingInputControl) -> IntuneMapping:
        return IntuneMapping(
            cis_id=control.control_id,
            title=control.title,
            implementation_type="endpoint_security",
            intune_area="BitLocker",
            setting_name="Disk encryption",
            value=control.default_value or "Use CIS recommended value",
            confidence=0.50,
            rule_id=self.rule_id,
        )


class CredentialGuardRule(MappingRule):
    rule_id = "endpoint_security.credential_guard"

    def matches(self, control: MappingInputControl) -> bool:
        t = control.title.lower()
        return "credential guard" in t or "virtualization based security" in t

    def apply(self, control: MappingInputControl) -> IntuneMapping:
        return IntuneMapping(
            cis_id=control.control_id,
            title=control.title,
            implementation_type="endpoint_security",
            intune_area="Credential Protection",
            setting_name="Credential Guard",
            value=control.default_value or "Use CIS recommended value",
            confidence=0.50,
            rule_id=self.rule_id,
        )


STARTER_RULES = [
    ConsumerExperienceRule(),
    DefenderRule(),
    FirewallRule(),
    BitLockerRule(),
    CredentialGuardRule(),
]
