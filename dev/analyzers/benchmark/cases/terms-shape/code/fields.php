<?php
/**
 * Turns a course post into the plain array the templates and the JSON feed use.
 */

defined( 'ABSPATH' ) || exit;

const CT_POST_TYPE = 'ct_course';
const CT_TOPIC     = 'ct_topic';
const CT_START     = 'ct_start';
const CT_END       = 'ct_end';
const CT_CITY      = 'ct_city';
const CT_URL       = 'ct_url';

/** Accepts `Y-m-d` only; anything else becomes an empty string. */
function ct_clean_date( string $value ): string {
	$value = trim( $value );
	$date  = DateTimeImmutable::createFromFormat( '!Y-m-d', $value );
	return ( $date && $date->format( 'Y-m-d' ) === $value ) ? $value : '';
}

/**
 * @return array{id:int,title:string,start:string,end:string,city:string,url:string,topics:string[]}|null
 */
function ct_shape( int $post_id ): ?array {
	if ( CT_POST_TYPE !== get_post_type( $post_id ) ) {
		return null;
	}

	$start = ct_clean_date( (string) get_post_meta( $post_id, CT_START, true ) );
	if ( '' === $start ) {
		return null;
	}

	$end = ct_clean_date( (string) get_post_meta( $post_id, CT_END, true ) );
	if ( '' !== $end && $end < $start ) {
		$end = '';
	}

	return [
		'id'     => $post_id,
		'title'  => html_entity_decode( get_the_title( $post_id ), ENT_QUOTES, 'UTF-8' ),
		'start'  => $start,
		'end'    => $end,
		'city'   => (string) get_post_meta( $post_id, CT_CITY, true ),
		'url'    => esc_url_raw( (string) get_post_meta( $post_id, CT_URL, true ) ),
		'topics' => wp_get_object_terms( $post_id, CT_TOPIC, [ 'fields' => 'names' ] ) ?: [],
	];
}

/** One line per course for the feed: "12.–14.03.2031 · Berlin · Topic A, Topic B". */
function ct_feed_line( array $course ): string {
	$range = ct_format_range( $course['start'], $course['end'] );
	$parts = array_filter( [ $range, $course['city'], implode( ', ', $course['topics'] ) ] );
	return implode( ' · ', $parts );
}

function ct_format_range( string $start, string $end ): string {
	$a = DateTimeImmutable::createFromFormat( '!Y-m-d', $start );
	if ( ! $a ) {
		return '';
	}
	if ( '' === $end || $end === $start ) {
		return $a->format( 'd.m.Y' );
	}
	$b = DateTimeImmutable::createFromFormat( '!Y-m-d', $end );
	if ( ! $b ) {
		return $a->format( 'd.m.Y' );
	}
	if ( $a->format( 'Y-m' ) === $b->format( 'Y-m' ) ) {
		return $a->format( 'd.' ) . '–' . $b->format( 'd.m.Y' );
	}
	return $a->format( 'd.m.' ) . '–' . $b->format( 'd.m.Y' );
}
