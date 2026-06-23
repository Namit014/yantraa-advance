import { Demo } from "@/components/demo";
import { AuthWrapper } from "@/components/auth-wrapper";

export default function Home() {
  return (
    <AuthWrapper>
      <div className="min-h-screen bg-black">
        <Demo />
      </div>
    </AuthWrapper>
  );
}
