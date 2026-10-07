# Gorden attribution and adaptation

Author: **Gorden Sun / @Gorden Sun**. Upstream: [GordenSuperPPTSkills](https://github.com/GordenSun/GordenSuperPPTSkills). Reviewed revision: `8c05583dab8334182b71738e8dfbbec5c56a1951` (2026-09-06).

- [GordenImagePPTGen](https://github.com/GordenSun/GordenSuperPPTSkills/blob/8c05583dab8334182b71738e8dfbbec5c56a1951/GordenImagePPTGen/SKILL.md): per-page self-contained prompt, actual output provenance, source copying and targeted retries informed image-deck.
- [GordenImage2PPTX](https://github.com/GordenSun/GordenSuperPPTSkills/blob/8c05583dab8334182b71738e8dfbbec5c56a1951/GordenImage2PPTX/SKILL.md): original pixel coordinates, proportional mapping, font-height conversion and final alignment review informed two-layer conversion.
- [README rights](https://github.com/GordenSun/GordenSuperPPTSkills/blob/8c05583dab8334182b71738e8dfbbec5c56a1951/README.md): requests GitHub/source-author attribution for commercial use. No MIT license is asserted here.

Local code was written for artifact-tool; upstream Python composition code was not copied. The two-layer conversion route retains background and text; the general design contract also uses background/structure/subjects/text as responsibilities, without requiring four images. No required frame/icon splitting, chroma key, dense framework, extra facts, mandatory cover, no-logo rule, hardcoded model or install step is adopted. This attribution is part of the portable skill package.


## PPT Master design references

[hugohe3/ppt-master](https://github.com/hugohe3/ppt-master/tree/440557b8dc7c7257b69c04a0b014d5c50a78e6cb), reviewed fixed revision `440557b8dc7c7257b69c04a0b014d5c50a78e6cb`: resource plans, target-region aspect/crop decisions, shared deck/image palette and data-driven chart geometry informed the Visual Contract. We do not import its full SVG/multi-role framework, mandatory style alternatives or external scripts. These are adapted design principles, not copied implementation code; upstream rights are not relicensed by this package.
