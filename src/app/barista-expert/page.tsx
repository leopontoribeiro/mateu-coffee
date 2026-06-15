import { BaristaExpert } from "@/components/BaristaExpert";

export const metadata = {
  title: "Barista Expert | Mateu Coffee",
  description: "IA especializada em café, equipamentos, técnicas e defeitos de extração",
};

export default function BaristaExpertPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      <div className="max-w-2xl mx-auto p-4 h-screen flex flex-col">
        <BaristaExpert />
      </div>
    </div>
  );
}
