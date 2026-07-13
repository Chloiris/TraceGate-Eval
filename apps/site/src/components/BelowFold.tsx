import { Architecture, FooterCta, Security, Verification } from "./ArchitectureTrust";
import { Capabilities, ProblemStory, ProofStrip } from "./ProofAndCapabilities";
import { ProductGallery } from "./ProductGallery";
import { AutofixWorkflow, CodeIntelligence, ReviewWorkflow } from "./Workflows";

export default function BelowFold() {
  return (
    <>
      <ProofStrip />
      <ProblemStory />
      <Capabilities />
      <ReviewWorkflow />
      <AutofixWorkflow />
      <CodeIntelligence />
      <ProductGallery />
      <Architecture />
      <Verification />
      <Security />
      <FooterCta />
    </>
  );
}
