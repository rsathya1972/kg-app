import Header from "@/components/Header";
import LeftNav from "@/components/LeftNav";

export default function MainLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Header />
      <div className="flex min-h-screen pt-14">
        <LeftNav />
        <main className="flex-1 ml-56 p-8 overflow-y-auto">{children}</main>
      </div>
    </>
  );
}
