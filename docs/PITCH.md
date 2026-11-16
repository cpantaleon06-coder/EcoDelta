# EcoDelta pitch

Spoken text, about one minute. Every number here comes from `ecodelta-engine/docs/VALIDATION.md` or
the validate command on the real export; see `docs/DESCRIPTION.md` for the sources.

---

Is the water cycle changing, and how sure can anyone be?

EcoDelta screens NASA data for rain, evaporation, surface runoff and soil moisture across 21 regions
of the world, from 2001 to 2025. For every region and variable it answers four questions: what
changed, where, by how much, and can we trust it. Each answer shows the trend with its uncertainty,
how much of the region has data, and which NASA product it comes from. Evidence and size are shown
apart, so a small, certain change is never confused with a large, uncertain one.

Our proudest result is one we did not publish. EcoDelta checks its own output. For air temperature,
it reproduced a NASA POWER regional trend to within about 1%, but POWER is built on the same MERRA-2
data, so that only proves our pipeline. Against an independent record, NASA GISTEMP, the MERRA-2
global warming trend came out about one third lower, and one region, the Sahel, showed a cooling we
could not confirm. So we held temperature back. For the water variables, every regional result is
compared with a second record, and the ones that disagree are held back too. EcoDelta shows what it
can defend, and tells you what it cannot.

[TODO: closing line with the protagonist question once it is chosen, see docs/DEMO.md.]

---

Do not say in the pitch:
- that any variable is validated (the water variables were compared only with references that are not
  independent of them, so their shown results are "limited");
- that Compare isolates the parts of two regions that do not overlap;
- anything about whole countries (regions are approximate boxes);
- that a trend has a cause.
