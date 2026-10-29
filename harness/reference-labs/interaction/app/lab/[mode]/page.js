import {notFound} from 'next/navigation';
import Link from 'next/link';
import ReviewTask from '../../../components/review-task';
const names={css:'CSS baseline',motion:'Motion',anime:'Anime.js','animate-css':'Animate.css',gsap:'GSAP'};
export function generateStaticParams(){return Object.keys(names).map(mode=>({mode}))}
export const dynamicParams=false;
export default async function Page({params}){const {mode}=await params;if(!names[mode])notFound();return <main className="mx-auto max-w-5xl px-5 py-8"><header><Link prefetch={false} className="back-link" href="/">← All modes</Link><p className="eyebrow mt-8">REFERENCE LAB · {names[mode]}</p><h1 className="text-3xl font-semibold tracking-tight">Review the delivery.</h1><p className="intro">Select a document, inspect its details, and mark it reviewed. Try reversing the reveal while it is running.</p></header><ReviewTask mode={mode} name={names[mode]}/><footer className="footnote">Static synthetic fixture · No server database · Browser-local state only</footer></main>}
