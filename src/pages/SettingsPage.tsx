import { Save, Bell, Shield, Clock, Database, Mail, Trash2 } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="max-w-4xl space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Workspace Settings</h2>
          <p className="text-slate-500 mt-1">Configure operational parameters and system behavior.</p>
        </div>
        <button className="flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-all shadow-sm">
          <Save className="w-4 h-4" />
          Save Settings
        </button>
      </div>

      <div className="space-y-6">
        <SettingsSection 
          title="Schedule & Automation" 
          description="Control when the intelligence cycle runs."
          icon={Clock}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-700">Run Frequency</label>
              <select className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none bg-white">
                <option>Every 4 hours</option>
                <option>Daily (08:00 AM)</option>
                <option>Daily (06:00 PM)</option>
                <option>Weekly (Monday AM)</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-700">Timezone</label>
              <select className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none bg-white">
                <option>UTC (Coordinated Universal Time)</option>
                <option>EST (Eastern Standard Time)</option>
                <option>PST (Pacific Standard Time)</option>
              </select>
            </div>
          </div>
        </SettingsSection>

        <SettingsSection 
          title="Report Generation" 
          description="Configure how reports are drafted and scored."
          icon={Database}
        >
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-700">Minimum Relevance Threshold</p>
                <p className="text-xs text-slate-500">Only items above this score will be included in reports.</p>
              </div>
              <div className="flex items-center gap-3">
                <input type="range" className="w-32 accent-indigo-600" min="0" max="100" defaultValue="75" />
                <span className="text-sm font-bold text-slate-900 w-8">75%</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-700">Report Style</p>
                <p className="text-xs text-slate-500">The verbosity and format of the generated intelligence.</p>
              </div>
              <select className="px-4 py-2 border border-slate-200 rounded-lg text-sm bg-white">
                <option>Executive Concise</option>
                <option>Detailed Analysis</option>
                <option>Bullet Points Only</option>
              </select>
            </div>
          </div>
        </SettingsSection>

        <SettingsSection 
          title="Notifications & Delivery" 
          description="Configure outbound delivery channels (Coming Soon)."
          icon={Mail}
        >
          <div className="space-y-4 opacity-60 grayscale pointer-events-none">
            <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border border-slate-100">
              <div className="flex items-center gap-3">
                <Mail className="w-5 h-5 text-slate-400" />
                <div>
                  <p className="text-sm font-semibold text-slate-700">Email Digest</p>
                  <p className="text-xs text-slate-500">Send reports directly to customer emails.</p>
                </div>
              </div>
              <div className="w-10 h-5 bg-slate-200 rounded-full" />
            </div>
          </div>
        </SettingsSection>

        <div className="p-6 bg-red-50 border border-red-100 rounded-xl space-y-4">
          <div className="flex items-center gap-3 text-red-700">
            <Trash2 className="w-5 h-5" />
            <h3 className="font-bold">Danger Zone</h3>
          </div>
          <p className="text-sm text-red-600">Deleting this workspace will permanently remove all feeds, content history, and reports. This action cannot be undone.</p>
          <button className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-bold transition-colors">
            Delete Workspace
          </button>
        </div>
      </div>
    </div>
  );
}

function SettingsSection({ title, description, icon: Icon, children }: { title: string, description: string, icon: any, children: React.ReactNode }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-sm space-y-6">
      <div className="flex items-start gap-4">
        <div className="p-2 bg-slate-50 text-slate-600 rounded-lg">
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-slate-900">{title}</h3>
          <p className="text-sm text-slate-500">{description}</p>
        </div>
      </div>
      <div className="pt-4 border-t border-slate-100">
        {children}
      </div>
    </div>
  );
}
